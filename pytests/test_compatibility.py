"""
This file is part of TexText, an extension for the vector
illustration program Inkscape.

Copyright (c) 2006-2025 TexText developers.

TexText is released under the 3-Clause BSD license. See
file LICENSE.txt or go to https://github.com/textext/textext
for full license details.
"""
import os
import pytest
import sys
import textext.base as textext
import tempfile
import subprocess
import shutil
import json
import PIL.Image

if os.name == "nt":
    EXTENSION_DIR = os.path.join(os.getenv("APPDATA"), "inkscape\\extensions\\textext")
    INKSCAPE_EXE = "C:\\Program Files\\Inkscape\\bin\\inkscape.com"
    COMPARE_EXE = ["C:\\Program Files\\ImageMagick-7.0.10-Q8\\magick", "compare"]
else:
    EXTENSION_DIR = os.path.expanduser("~/.config/inkscape/extensions/textext")
    INKSCAPE_EXE = "inkscape"
    COMPARE_EXE = ["compare"]

# Set this to False to keep results in separate pytests_results folder
RESULTS_INTO_TEMPDIR = True


class TempDirectory(object):

    def __init__(self, suffix=""):
        self.__name = None
        self.__suffix = suffix

    def __enter__(self):
        if RESULTS_INTO_TEMPDIR:
            self.__name = tempfile.mkdtemp()
        else:
            dn = os.path.join(os.getcwd(), "pytests_results", self.__suffix)
            if not os.path.exists(dn):
                os.makedirs(dn)  # ToDo: Make use of exist_ok flag when porting to Python 3.7
            self.__name = dn
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (self.__name is not None) and RESULTS_INTO_TEMPDIR:
            shutil.rmtree(self.__name)

    @property
    def name(self):
        return self.__name


def svg_to_png(svg, png, dpi=None, height=None, render_area="drawing"):
    assert os.path.isfile(svg)
    options = []
    if dpi:
        options.append("--export-dpi=%d" % dpi)
    if height:
        options.append("--export-height=%d" % height)
    if render_area == "drawing":
        options.append("--export-area-drawing")
    elif render_area == "document":
        pass
    else:
        raise RuntimeError("Unknwon export option `%s`" % render_area)

    subprocess.call([INKSCAPE_EXE, "--export-type=png"] + options + ["--export-filename=%s" % png] + [svg],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    assert os.path.isfile(png)


def images_are_same(png1, png2, fuzz="0%", size_abs_tol=10, size_rel_tol=0.005, pixel_diff_abs_tol=0,
                    pixel_diff_rel_tol=0.0):
    """
    :param (str) png1: path to first image
    :param (str) png2: path to second image
    :param (str) fuzz: colors within this distance are considered equal
    :param (int) size_abs_tol: absolute size tolerance (in pixels)
    :param (float) size_rel_tol: relative size tolerance
    :param (int) pixel_diff_abs_tol: max number of different pixels
    :param (float) pixel_diff_rel_tol: max relative number of different pixels of image size
    :return (bool, str): pair of check result and message
    """

    assert os.path.isfile(png1)
    assert os.path.isfile(png2)

    im1 = PIL.Image.open(png1)
    im2 = PIL.Image.open(png2)

    dw = im2.width - im1.width
    dh = im2.height - im1.height

    w = min(im2.width, im1.width)
    h = min(im2.height, im1.height)

    if dw != 0:
        sys.stderr.write("Images width differ by %d px\n" % dw)

    if dh != 0:
        sys.stderr.write("Images height differ by %d px\n" % dh)

    if dw > size_abs_tol or \
            dh > size_abs_tol or \
            dw > w * size_rel_tol or \
            dh > h * size_rel_tol:
        return False, "Images have too different sizes: %s vs %s\n" % (str(im1.size), str(im2.size))

    if dh != 0 or dw != 0:
        size_abs_tol //= 2
        pixel_diff_abs_tol //= 2
        w //= 2
        h //= 2
        sys.stderr.write("Images are downsampled to (%d, %d)\n" % (w, h))

    im1.resize((w, h), PIL.Image.LANCZOS).save(png1)
    im2.resize((w, h), PIL.Image.LANCZOS).save(png2)

    proc = subprocess.Popen(COMPARE_EXE + ["-channel", "rgba", "-metric", "ae",
                                           "-fuzz", fuzz, png1, png2,
                                           os.devnull if RESULTS_INTO_TEMPDIR else
                                           os.path.join(os.path.dirname(png1), "diff.png")],
                            stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    stdout, stderr = proc.communicate()

    if proc.returncode in [0, 1]:
        try:
            diff_pixels = int(stderr.decode("utf-8"))
        except (ValueError, AttributeError):
            return False, "Can't parse `compare` output"

        if diff_pixels > pixel_diff_abs_tol:
            return False, "diff pixels (%d) > %d" % (diff_pixels, pixel_diff_abs_tol)

        if diff_pixels > w * h * pixel_diff_rel_tol:
            return False, "diff pixels (%d) > W*H*%f (%f)" % (
                diff_pixels, pixel_diff_rel_tol, w * h * pixel_diff_rel_tol)

        return True, "diff pixels (%d)" % diff_pixels
    else:
        if stdout: sys.stdout.write(stdout)
        if stderr: sys.stderr.write(stderr)
        return False, "`compare` return code is %d " % proc.returncode


def is_current_version_compatible(test_id,
                                  svg_original,
                                  svg_modified,
                                  json_config,
                                  converter,
                                  fuzz=None,
                                  pixel_diff_abs_tol=50,
                                  pixel_diff_rel_tol=0.001
                                  ):
    """
    :param (str) test_id: A string characterizing the test. Used in tmp dirs.
    :param (str) svg_original: path to snippet
    :param (str) svg_modified: path to empty svg created with same version of inkscape as `svg_snippet`
    :param (str) json_config: path to json config
    :param (str) converter: "pstoedit" or "pdf2svg"
    :param (str) fuzz: overwrite fuzz from config
    :param (int) pixel_diff_abs_tol: max number of different pixels
    :param (float) pixel_diff_rel_tol: max relative number of different pixels of image size
    """

    assert os.path.isfile(svg_original)
    assert os.path.isfile(svg_modified)
    assert os.path.isfile(json_config)
    assert converter in ["inkscape", "pstoedit", "pdf2svg"]

    with TempDirectory(test_id) as tempdir:
        tmp_dir = tempdir.name

        png1 = os.path.join(tmp_dir, "1.png")
        png2 = os.path.join(tmp_dir, "2.png")

        config = json.load(open(json_config, encoding="utf-8"))
        check_render = config["check"]["render"]

        render_options = {}
        if check_render:
            if check_render["scale-is-preserved"]:
                assert "height" not in check_render
                render_options["dpi"] = check_render.get("dpi", 90)
            else:
                assert "dpi" not in check_render
                render_options["height"] = check_render.get("height", 100)

            render_options["render_area"] = check_render.get("render-area", "document")

        svg_to_png(svg_modified, png1, **render_options)

        # inherit all from original
        mod_args = config["original"]  # type: dict
        # overwrite with modified
        mod_args.update(config["modified"])

        # Assing the preamble file: If no one is specified at all, use the default preamble file
        # from the extension directory. If no file with the specified name exist try to look in the
        # snippet dir. If this fails, too, use the default preamble from the extension dir
        extension_dir_preamble_file = os.path.join(EXTENSION_DIR, "default_packages.tex")
        if "preamble-file" not in mod_args or not mod_args["preamble-file"]:
            mod_args["preamble-file"] = extension_dir_preamble_file
        else:
            if not os.path.isfile(mod_args["preamble-file"]):
                snippet_dir_preamble_file = os.path.join(
                    os.path.dirname(os.path.abspath(json_config)),
                    mod_args["preamble-file"])
                if os.path.isfile(snippet_dir_preamble_file):
                    mod_args["preamble-file"] = snippet_dir_preamble_file
                else:
                    mod_args["preamble-file"] = extension_dir_preamble_file

        if "alignment" not in mod_args:
            mod_args["alignment"] = "middle center"

        # run TexText
        tt = textext.TexText()
        tt.run([
            r"--id=%s" % "content",  # todo: find a TexText node to avoid hard-coded ids
            r"--text=%s" % mod_args["text"],
            r"--scale-factor=%f" % mod_args["scale-factor"],
            r"--preamble-file=%s" % mod_args["preamble-file"],
            r"--alignment=%s" % mod_args["alignment"],
            svg_original], output=os.devnull)

        svg2 = os.path.join(tmp_dir, "svg2.svg")

        tt.document.write(svg2)

        svg_to_png(svg2, png2, **render_options)

        if not fuzz:
            fuzz = config["check"]["compare"].get("fuzz", "0%")

        return images_are_same(png1, png2,
                               fuzz=fuzz,
                               pixel_diff_abs_tol=pixel_diff_abs_tol,
                               pixel_diff_rel_tol=pixel_diff_rel_tol
                               )


def test_compatibility(root, inkscape_version, textext_version, converter, test_case):
    if inkscape_version.startswith("_") or textext_version.startswith("_") or converter.startswith(
            "_") or test_case.startswith("_"):
        pytest.skip("skip %s (remove underscore to enable)" % os.path.join(inkscape_version, textext_version, converter,
                                                                           test_case))
    test_id = "%s-%s-%s-%s" % (inkscape_version, textext_version, converter, test_case)
    result, message = is_current_version_compatible(
        test_id,
        svg_original=os.path.join(root, inkscape_version, textext_version, converter, test_case, "original.svg"),
        svg_modified=os.path.join(root, inkscape_version, textext_version, converter, test_case, "modified.svg"),
        json_config=os.path.join(root, inkscape_version, textext_version, converter, test_case, "config.json"),
        converter=converter
    )
    sys.stderr.write(message + "\n")
    assert result, message
