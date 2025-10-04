import argparse

from audio_tool.core import (
    list_sessions_verbose,
    set_volume_by_name,
    interactive_set_volume,
    toggle_volume
)


def main():
    parser = argparse.ArgumentParser(description="Control application volumes on Windows")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all audio applications active")

    # select
    subparsers.add_parser("select", help="Interactively select an application and change its volume")

    # set
    set_parser = subparsers.add_parser("set", help="Set volume for an application")
    set_parser.add_argument("app_name")
    set_parser.add_argument("volume")

    # toggle
    toggle_parser = subparsers.add_parser("toggle", help="Toggle mute for an app")
    toggle_parser.add_argument("app_name")

    # cdda
    subparsers.add_parser("cdda", help="Toggle CDDA's volume on and off")

    args = parser.parse_args()

    match args.command:
        case "list":
            for session in list_sessions_verbose():
                print(session)
        case "select":
            result = interactive_set_volume()
            if result.error:
                print(result.error.value)
            else:
                print(f"Set {result.name} volume to {result.volume * 100:.0f}%")

        case "set":
            result = set_volume_by_name(args.app_name, args.volume)
            if result.error:
                print(result.error.value)
            else:
                print(f"Set {args.app_name} volume to {result.volume * 100:.0f}%")
        case "toggle":
            result = toggle_volume(args.app_name)
            if result.error:
                print(result.error.value)
            else:
                print(f"Set {args.app_name} volume to {result.volume * 100:.0f}%")
        case "cdda":
            # Special case for Cataclysm DDA
            new_vol = toggle_volume("cataclysm-tiles.exe")
            if new_vol.error:
                print("There was an error in the process: " + new_vol.error.value)
            else:
                print(f"CDDA volume set to {new_vol.volume * 100:.0f}%")



if __name__ == "__main__":
    main()