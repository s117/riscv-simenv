import os


def get_template_content(template_name):
    # type: (str) -> str
    template_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        f"{template_name}.template"
    )
    with open(template_path, "r") as fp:
        template_content = fp.read()
    return template_content


def instantiate_template(template_name, **kwargs):
    # type: (str, **str) -> str
    template_content = get_template_content(template_name)
    return template_content.format(**kwargs)
