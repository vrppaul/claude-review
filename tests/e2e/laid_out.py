"""What the browser tests ask of how an element is laid out: whether all of it shows across, and how tall a token stands."""

# Whether an element, and everything in it, shows its contents whole across: nothing cut off, nothing to scroll sideways
SHOWN_WHOLE_ACROSS = "(element) => [element, ...element.querySelectorAll('*')].every((inside) => inside.scrollWidth <= inside.clientWidth)"
# How tall a box stands that a token of the stylesheet says the height of, in pixels
TALL_AS_ITS_TOKEN = """(token) => {
    const probe = document.createElement('div');
    probe.style.height = `var(${token})`;
    document.body.append(probe);
    const height = probe.getBoundingClientRect().height;
    probe.remove();
    return height;
}"""
