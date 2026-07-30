"""
FoodTrack Server -- Entry Point
  python run.py              (starts on port 8000)
  python run.py 8080         (starts on custom port)
  Ctrl+C to stop the server
"""
import sys, os, logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-7s %(name)-18s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

from app.main import app

if __name__ == "__main__":
    import uvicorn

    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    sep = "=" * 56
    print("")
    print(sep)
    print("  FoodTrack - Digital Trust Infrastructure")
    print(sep)
    print("  Server   : http://{}:{}".format(host, port))
    print("  Docs     : http://{}:{}/docs".format(host, port))
    print("  Frontend : http://{}:{}/".format(host, port))
    print("  API      : http://{}:{}/api/v1/search".format(host, port))
    print("")
    print("  Ctrl+C to stop the server")
    print(sep)
    print("")
    sys.stdout.flush()

    uvicorn.run(
        "run:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
        access_log=True,
    )
