"""python -m closet web|bot"""
import sys

from .config import Settings
from .service import build


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "web"
    s = Settings.from_env()
    closet = build(s)
    if mode == "bot":
        from .telegram_bot import run

        run(closet, s.telegram_token, s.telegram_allowed)
    elif mode == "web":
        import uvicorn

        from .api import create_app

        uvicorn.run(create_app(closet), host="0.0.0.0", port=int(sys.argv[2]) if len(sys.argv) > 2 else 8085)
    elif mode == "import":
        from .importer import import_folder

        done, errors = import_folder(closet, sys.argv[2])
        print(f"{len(done)} prendas importadas")
        for e in errors:
            print("⚠️", e)
    else:
        sys.exit("uso: python -m closet [web [puerto]|bot|import CARPETA]")


if __name__ == "__main__":
    main()
