{ pkgs }: {
  deps = [
    pkgs.ffmpeg
    pkgs.espeak-ng
    pkgs.fontconfig
    pkgs.dejavu_fonts
  ];
  env = { FONTCONFIG_FILE = pkgs.makeFontsConf { fontDirectories = [ pkgs.dejavu_fonts ]; }; };
}
