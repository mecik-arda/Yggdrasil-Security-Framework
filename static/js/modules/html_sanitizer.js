(function (global) {
    const allowedTags = new Set([
        'A', 'B', 'BLOCKQUOTE', 'BR', 'CODE', 'DIV', 'EM', 'H1', 'H2', 'H3',
        'H4', 'H5', 'H6', 'HR', 'I', 'LI', 'OL', 'P', 'PRE', 'SPAN', 'STRONG',
        'TABLE', 'TBODY', 'TD', 'TFOOT', 'TH', 'THEAD', 'TR', 'UL'
    ]);
    const allowedAttributes = new Set([
        'aria-label', 'class', 'colspan', 'href', 'rel', 'role', 'rowspan',
        'target', 'title'
    ]);
    const allowedProtocols = new Set(['http:', 'https:', 'mailto:']);

    function isSafeUrl(value) {
        const normalizedValue = String(value || '').trim();
        if (normalizedValue.startsWith('#') || normalizedValue.startsWith('/')) return true;
        try {
            return allowedProtocols.has(new URL(normalizedValue, document.baseURI).protocol);
        } catch (error) {
            return false;
        }
    }

    function sanitizeHtml(value) {
        const template = document.createElement('template');
        template.innerHTML = String(value || '');
        Array.from(template.content.querySelectorAll('*')).forEach(function (element) {
            if (!allowedTags.has(element.tagName)) {
                element.remove();
                return;
            }
            Array.from(element.attributes).forEach(function (attribute) {
                const attributeName = attribute.name.toLowerCase();
                if (!allowedAttributes.has(attributeName)) {
                    element.removeAttribute(attribute.name);
                    return;
                }
                if (attributeName === 'href' && !isSafeUrl(attribute.value)) {
                    element.removeAttribute(attribute.name);
                }
                if (attributeName === 'target' && !['_blank', '_self'].includes(attribute.value)) {
                    element.removeAttribute(attribute.name);
                }
            });
            if (element.tagName === 'A' && element.getAttribute('target') === '_blank') {
                element.setAttribute('rel', 'noopener noreferrer');
            }
        });
        return template.innerHTML;
    }

    function setSanitizedHtml(element, value) {
        if (element) element.innerHTML = sanitizeHtml(value);
    }

    function safeExternalUrl(value) {
        return isSafeUrl(value) ? String(value) : '#';
    }

    global.sanitizeHtml = sanitizeHtml;
    global.setSanitizedHtml = setSanitizedHtml;
    global.safeExternalUrl = safeExternalUrl;
})(window);
