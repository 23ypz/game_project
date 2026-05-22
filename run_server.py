import argparse
import asyncio

from server.server_app import run_server


def main():
    parser = argparse.ArgumentParser(description="多边形游戏多人联机服务器")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    asyncio.run(run_server(args.host, args.port))


if __name__ == "__main__":
    main()
