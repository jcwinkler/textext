from textext.converter import TexToPdfConverter

preamble_0 = """\\documentclass[10pt]{article}
\\usepackage{amsmath}
"""

preamble_0_result = """\\usepackage{amsmath}
"""

preamble_1 = """\\documentclass[10pt]
{article}
\\usepackage{amsmath}
"""

preamble_1_result = """\\usepackage{amsmath}
"""

preamble_2 = """\\documentclass[10pt]
{article
}
\\usepackage{amsmath}
"""

preamble_2_result = """\\usepackage{amsmath}
"""

preamble_3 = """
   \\documentclass[10pt]
{article}
\\usepackage{amsmath}
"""

preamble_3_result = """   
   \\usepackage{amsmath}
"""

preamble_4 = """\\documentstyle[10pt]{article}
\\usepackage{amsmath}
"""

preamble_4_result = """\\usepackage{amsmath}
"""

preamble_5 = """\\usepackage{amsmath}
"""

preamble_5_result = """\\usepackage{amsmath}
"""


def test__remove_documentclass():
    for preamble, preamble_result in [[preamble_0, preamble_0_result], [preamble_1, preamble_1_result],
                                      [preamble_2, preamble_2_result], [preamble_3, preamble_3_result],
                                      [preamble_4, preamble_4_result], [preamble_5, preamble_5_result]]:
        assert preamble_result == TexToPdfConverter._remove_documentclass(preamble)
