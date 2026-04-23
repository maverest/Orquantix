import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_for_server(port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    return False


def get_data_dir() -> Path:
    app_support = Path.home() / "Library" / "Application Support"
    preferred = app_support / "Orquantix"
    legacy = app_support / "Semantix"

    if preferred.exists() or not legacy.exists():
        return preferred

    try:
        legacy.rename(preferred)
        return preferred
    except OSError:
        return legacy


def main() -> None:
    # When bundled by PyInstaller, resources live in sys._MEIPASS
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        os.environ["SEMANTIX_TEMPLATES"] = str(base / "templates")
        os.environ["SEMANTIX_STATIC"] = str(base / "static")

    design_mode = "--design" in sys.argv
    port = find_free_port()
    data_dir = get_data_dir()

    from app import AppState, create_app, start_background

    state = AppState()
    flask_app = create_app(state)
    start_background(state, data_dir)

    server_thread = threading.Thread(
        target=lambda: flask_app.run(
            host="127.0.0.1",
            port=port,
            debug=False,
            use_reloader=False,
        ),
        daemon=True,
    )
    server_thread.start()

    if not wait_for_server(port):
        print(f"[Orquantix] Server did not respond on port {port} within 15 s.")
        return

    url = f"http://127.0.0.1:{port}"

    if design_mode:
        # Open in default browser for design iteration with DevTools
        webbrowser.open(url)
        server_thread.join()
    else:
        # Open in native window (no browser needed)
        import webview
        window = webview.create_window(
            title="Orquantix",
            url=url,
            width=720,
            height=900,
            resizable=True,
            min_size=(480, 600),
        )
        webview.start()


if __name__ == "__main__":
    main()
