{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    python3Packages.pip
    python3Packages.virtualenv
    python3Packages.cocotb
    gtkwave
    verilog
    yosys
    gnumake
  ];

  shellHook = ''
    echo "Available tools:"
    echo "  Python: $(python3 --version)"
    echo "  GTKWave: $(gtkwave --version 2>&1 | head -n1)"
    echo "  Icarus Verilog: $(iverilog -V 2>&1 | head -n1)"
    echo "  CocoTB: $(python3 -c 'import cocotb; print(cocotb.__version__)' 2>/dev/null || echo 'installed')"
  '';
}
