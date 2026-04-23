from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

import requests

if TYPE_CHECKING:
    from app import AppState

LEXIQUE_URL = "http://www.lexique.org/databases/Lexique383/Lexique383.tsv"
LEXIQUE_FILENAME = "Lexique383.tsv"
MODEL_URL = "https://embeddings.net/embeddings/frWiki_no_phrase_no_postag_1000_skip_cut200.bin"
MODEL_FILENAME = "frWiki_no_phrase_no_postag_1000_skip_cut200.bin"


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


def download_all(state: AppState, data_dir: Path) -> None:
    """
    Download Lexique383 (if missing) then model (if missing).
    Updates state.progress and state.detail throughout.
    Lexique = 0→5%, model = 5→100%.
    """
    def on_progress(pct: int, detail: str) -> None:
        state.update(progress=pct, detail=detail)

    lexique_path = data_dir / LEXIQUE_FILENAME
    model_path = data_dir / MODEL_FILENAME

    if not lexique_path.exists():
        on_progress(0, "Téléchargement de Lexique383…")
        download_file(LEXIQUE_URL, lexique_path, on_progress, 0, 5)

    if not model_path.exists():
        on_progress(5, "Téléchargement du modèle Word2Vec…")
        download_file(MODEL_URL, model_path, on_progress, 5, 100)

    on_progress(100, "Téléchargement terminé.")
