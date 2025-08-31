{ pkgs, lib, config, inputs, devenv-zsh, ... }:

{
  # Use zsh as default shell
  imports = [ devenv-zsh.plugin ];
  zsh.enable = true;

  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = [
    pkgs.cocogitto
  ];

  # Secrets can be set in an .env file. Change to true if needed.
  # https://devenv.sh/reference/options/#dotenvenable
  dotenv.enable = false;

  languages.python = {
    enable = true;
    package = pkgs.python312;
    poetry = {
      enable = true;
      activate.enable = true;
      install.enable = true;
      install.quiet = true;
    };
  };

  # https://devenv.sh/tasks/
  # tasks = {
  #   "myproj:setup".exec = "mytool build";
  #   "devenv:enterShell".after = [ "myproj:setup" ];
  # };

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Starting tests..."
    echo ":: Running 'poetry install'"
    poetry install

    echo ":: Running import checks"
    cat << 'EOF' | python3 -
    #!/usr/bin/env python3

    # Trying native packages should be entirely unnecessary, but might as well sanity check.
    packages = [
        'os',
        'json',
        'logging',
        'structlog',
        'orjson',
        'colorama',
        'rich',
    ]

    # Loop through the packages list.
    missing_packages = []
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"The following packages failed to import: {', '.join(missing_packages)}")
        exit(1)
    else:
        print("All required packages are available.")
    EOF
  '';

  # https://devenv.sh/git-hooks/
  # git-hooks.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
