{
	inputs = {
		nixpkgs.url = "github:nixos/nixpkgs/release-25.05";
		flake-utils.url = "github:numtide/flake-utils";
	};

	outputs = { self, nixpkgs, flake-utils }:
		flake-utils.lib.eachDefaultSystem (system:
			let pkgs = import nixpkgs {
				inherit system;
			}; in {
				devShell = pkgs.mkShell {
					packages = with pkgs; [
						python313
						uv
					];
					shellHook = ''
						export UV_PYTHON="$(command -v python3.13)"
					'';
				};
			}
		);
}
