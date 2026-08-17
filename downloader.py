from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import requests

if TYPE_CHECKING:
    from games.orquantix.state import OrquantixState


@dataclass(frozen=True)
class Download:
    url: str
    filename: str
    share: int  # part de la barre de progression globale


DOWNLOADS: tuple[Download, ...] = (
    Download(
        url="http://www.lexique.org/databases/Lexique383/Lexique383.tsv",
        filename="Lexique383.tsv",
        share=14,
    ),
    Download(
        url="https://embeddings.net/embeddings/frWiki_no_phrase_no_postag_1000_skip_cut200.bin",
        filename="frWiki_no_phrase_no_postag_1000_skip_cut200.bin",
        share=70,
    ),
    Download(
        url="https://archive.org/download/XMLittre.dict/XMLittre.dict.dz",
        filename="XMLittre.dict.dz",
        share=15,
    ),
    Download(
        url="https://archive.org/download/XMLittre.dict/XMLittre.idx",
        filename="XMLittre.idx",
        share=1,
    ),
)

LEXIQUE_FILENAME = DOWNLOADS[0].filename
MODEL_FILENAME = DOWNLOADS[1].filename


def download_file(
    url: str,
    dest: Path,
    on_progress: Callable[[int, str], None],
    start_pct: int,
    end_pct: int,
) -> None:
    """
    Stream-download url → dest.
    Calls on_progress(pct, detail) after each chunk.
    pct is interpolated between start_pct and end_pct.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_dest = dest.with_suffix(dest.suffix + '.part')
    if temp_dest.exists():
        temp_dest.unlink()

    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(temp_dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65_536):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    file_ratio = downloaded / total
                    pct = int(start_pct + file_ratio * (end_pct - start_pct))
                    detail = (
                        f"{dest.name}… "
                        f"{downloaded // 1_000_000} Mo / {total // 1_000_000} Mo"
                    )
                else:
                    pct = start_pct
                    detail = f"{dest.name}… {downloaded // 1_000_000} Mo"
                on_progress(pct, detail)

        if total and downloaded != total:
            raise RuntimeError(
                f"Téléchargement incomplet pour {dest.name}: {downloaded} octets reçus sur {total}."
            )

        temp_dest.replace(dest)
    except Exception:
        if temp_dest.exists():
            temp_dest.unlink()
        raise


def missing_files(data_dir: Path) -> list[str]:
    """Les fichiers déclarés qui ne sont pas encore sur le disque."""
    return [spec.filename for spec in DOWNLOADS if not (data_dir / spec.filename).exists()]


def download_all(state: "OrquantixState", data_dir: Path) -> None:
    """Télécharge les fichiers manquants, en répartissant la progression."""

    def on_progress(pct: int, detail: str) -> None:
        state.update(progress=pct, detail=detail)

    start = 0
    for spec in DOWNLOADS:
        end = start + spec.share
        destination = data_dir / spec.filename
        if not destination.exists():
            on_progress(start, f"Téléchargement de {spec.filename}…")
            download_file(spec.url, destination, on_progress, start, end)
        start = end

    on_progress(100, "Téléchargement terminé.")
