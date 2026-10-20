"""
Unit tests for auto_apply.form_utils — the shared ATS form-filling logic.

Playwright is never launched; a tiny fake DOM stands in for a Page/element so we
can exercise the pure decision logic (especially the truthful sponsorship
answer) deterministically.
"""

from auto_apply import form_utils as fu


class FakeEl:
    """Minimal stand-in for a Playwright element handle."""

    def __init__(self, attrs=None, text="", visible=True, selectable=None):
        self.attrs = attrs or {}
        self.text = text
        self.visible = visible
        self.selectable = selectable  # set of labels select_option accepts
        self.filled = None
        self.clicked = False
        self.files = None
        self.selected = None
        self._sel = {}       # selector -> element
        self._sel_all = {}   # selector -> [elements]

    # queries
    def query_selector(self, s):
        return self._sel.get(s)

    def query_selector_all(self, s):
        return self._sel_all.get(s, [])

    # attribute / text
    def get_attribute(self, k):
        return self.attrs.get(k)

    def inner_text(self):
        return self.text

    def is_visible(self):
        return self.visible

    # actions
    def fill(self, v):
        self.filled = v

    def click(self):
        self.clicked = True

    def set_input_files(self, p):
        self.files = p

    def select_option(self, label=None):
        if self.selectable is not None and label not in self.selectable:
            raise ValueError("no such option")
        self.selected = label


WA_FULL = {
    "authorized_to_work_in_us": True,
    "requires_sponsorship_internship": False,
    "requires_sponsorship_fulltime": True,
    "will_relocate": True,
    "expected_graduation": "May 2027",
    "gpa": "4.0",
}


# ---- requires_sponsorship (the correctness-sensitive bit) -------------------

def test_requires_sponsorship_true_for_fulltime():
    assert fu.requires_sponsorship(WA_FULL) is True


def test_requires_sponsorship_false_when_neither():
    wa = {"requires_sponsorship_fulltime": False, "requires_sponsorship_internship": False}
    assert fu.requires_sponsorship(wa) is False


def test_requires_sponsorship_defaults_true():
    # An F-1 profile that omits the flags should default to needing sponsorship,
    # never silently claim it doesn't.
    assert fu.requires_sponsorship({}) is True


# ---- fill_field ------------------------------------------------------------

def test_fill_field_fills_first_matching_variant():
    page = FakeEl()
    target = FakeEl()
    page._sel["#email"] = target
    assert fu.fill_field(page, "#missing, #email", "a@b.com") is True
    assert target.filled == "a@b.com"


def test_fill_field_empty_value_is_noop():
    page = FakeEl()
    assert fu.fill_field(page, "#x", "") is False


def test_fill_field_optional_missing_returns_false():
    page = FakeEl()
    assert fu.fill_field(page, "#x", "v", optional=True) is False


# ---- upload_resume ---------------------------------------------------------

def test_upload_resume_attaches(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_text("pdf")
    page = FakeEl()
    file_input = FakeEl()
    page._sel["input[type='file']"] = file_input
    assert fu.upload_resume(page, resume) is True
    assert file_input.files == str(resume)


def test_upload_resume_missing_file(tmp_path):
    page = FakeEl()
    assert fu.upload_resume(page, tmp_path / "nope.pdf") is False


# ---- answer_yes_no ---------------------------------------------------------

def test_answer_yes_no_clicks_matching_radio():
    yes = FakeEl(attrs={"value": "yes"})
    no = FakeEl(attrs={"value": "no"})
    container = FakeEl()
    container._sel_all["input[type='radio']"] = [yes, no]
    assert fu.answer_yes_no(container, True) is True
    assert yes.clicked and not no.clicked


def test_answer_yes_no_uses_label_text():
    r_yes = FakeEl(attrs={"id": "r1"})
    r_no = FakeEl(attrs={"id": "r2"})
    container = FakeEl()
    container._sel_all["input[type='radio']"] = [r_yes, r_no]
    container._sel["label[for='r1']"] = FakeEl(text="Yes")
    container._sel["label[for='r2']"] = FakeEl(text="No")
    assert fu.answer_yes_no(container, False) is True
    assert r_no.clicked and not r_yes.clicked


def test_answer_yes_no_select_fallback():
    container = FakeEl()
    container._sel_all["input[type='radio']"] = []
    select = FakeEl(selectable={"Yes"})
    container._sel["select"] = select
    assert fu.answer_yes_no(container, True) is True
    assert select.selected == "Yes"


# ---- answer_custom_questions ----------------------------------------------

def _question(label_text):
    q = FakeEl()
    q._sel["label"] = FakeEl(text=label_text)
    return q


def test_custom_questions_sponsorship_answered_truthfully():
    q = _question("Will you now or in the future require visa sponsorship?")
    yes = FakeEl(attrs={"value": "yes"})
    no = FakeEl(attrs={"value": "no"})
    q._sel_all["input[type='radio']"] = [yes, no]
    page = FakeEl()
    page._sel_all[".q"] = [q]
    n = fu.answer_custom_questions(page, {}, WA_FULL, ".q")
    assert n == 1
    assert yes.clicked and not no.clicked  # truthful: full-time needs sponsorship


def test_custom_questions_authorized_answered_yes():
    q = _question("Are you legally authorized to work in the US?")
    yes = FakeEl(attrs={"value": "yes"})
    no = FakeEl(attrs={"value": "no"})
    q._sel_all["input[type='radio']"] = [yes, no]
    page = FakeEl()
    page._sel_all[".q"] = [q]
    fu.answer_custom_questions(page, {}, WA_FULL, ".q")
    assert yes.clicked and not no.clicked


def test_custom_questions_gpa_and_graduation_filled():
    text_sel = ("input[type='text'], input[type='date'], input[type='number'], "
                "input:not([type]), textarea")
    gpa_q = _question("What is your GPA?")
    gpa_input = FakeEl()
    gpa_q._sel[text_sel] = gpa_input
    grad_q = _question("Expected graduation date")
    grad_input = FakeEl()
    grad_q._sel[text_sel] = grad_input
    page = FakeEl()
    page._sel_all[".q"] = [gpa_q, grad_q]
    fu.answer_custom_questions(page, {}, WA_FULL, ".q")
    assert gpa_input.filled == "4.0"
    assert grad_input.filled == "May 2027"
