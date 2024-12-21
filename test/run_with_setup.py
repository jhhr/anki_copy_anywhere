import sys
import os


def setup_environment(script_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)

    # Calculate the package name
    relative_path = os.path.relpath(script_path, project_root)
    package_name = os.path.dirname(relative_path).replace(os.path.sep, ".")

    return package_name


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_with_setup.py <script> [args...]")
        sys.exit(1)

    script = sys.argv[1]
    # script_args = sys.argv[2:]

    package_name = setup_environment(script)

    with open(script, encoding="utf-8") as f:
        code = compile(f.read(), script, "exec")
        exec(
            code,
            {
                "__name__": "__main__",
                "__file__": script,
                "__package__": package_name if package_name else None,
                "sys": sys,
                "os": os,
            },
        )


if __name__ == "__main__":
    main()
