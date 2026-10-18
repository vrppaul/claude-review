"""What the browser tests ask of the colour words are drawn in: an element's own, and the one a token names."""

# The colour an element's words are drawn in, as the browser works it out
WORDS_COLOUR = "(element) => getComputedStyle(element).color"
# The colour words that step back are drawn in, in the theme the page is in: a probe drawn in that token, read as
# the browser works it out, so it compares with an element's own
FAINT_WORDS = """() => {
    const probe = document.createElement('span');
    probe.style.color = 'var(--cr-faint)';
    document.body.append(probe);
    const faint = getComputedStyle(probe).color;
    probe.remove();
    return faint;
}"""
