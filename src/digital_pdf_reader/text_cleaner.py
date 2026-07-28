"""
Text cleaning for digital-PDF extraction: doubled-character repair, Arabic
visual-order repair, and cid/control-character stripping.

Deliberately does not strip Arabic characters or markdown markup from field
values -- that's a downstream, schema-specific policy (e.g. an app that only
wants English values in a structured field), not a property of "reading a
digital PDF." Consumers that need that should layer it on top of this
module's output, in their own codebase.
"""

from __future__ import annotations

import re
import unicodedata

_CID_PATTERN = re.compile(r"\(cid:\d+\)")


class TextCleaner:
    """Doubled-char fix, Arabic-visual-order fix, and cid/control-char
    stripping for full document text."""

    def clean_full_text(self, text: str) -> str:
        """Full cleaning chain for a document's raw extracted text: doubled-char
        fix, then Arabic-reversal fix (only if Arabic is present), then
        cid/control-char stripping last."""
        if not text:
            return text
        text = self._fix_doubled_text(text)
        if self.has_arabic(text):
            text = self._fix_arabic_reversed(text)
        return self.strip_cid_and_control(text)

    def clean_table(self, table: list[list[str]]) -> list[list[str]]:
        return [[self._clean_cell(cell) for cell in row] for row in table]

    def _clean_cell(self, value: object) -> str:
        text = self.strip_cid_and_control("" if value is None else str(value))
        return " ".join(text.split())

    def strip_cid_and_control(self, text: str) -> str:
        text = _CID_PATTERN.sub("", text)
        cleaned = [
            ch
            for ch in text
            if not (unicodedata.category(ch) == "Cc" and ch not in ("\n", "\t", " "))
            and unicodedata.category(ch) not in ("Co", "Cs")
        ]
        return "".join(cleaned).strip()

    def has_arabic(self, text: str) -> bool:
        return any(self.is_arabic_char(ch) for ch in text)

    def is_arabic_char(self, ch: str) -> bool:
        code = ord(ch)
        return (
            (0x0600 <= code <= 0x06FF)
            or (0x0750 <= code <= 0x077F)
            or (0x08A0 <= code <= 0x08FF)
            or (0xFB50 <= code <= 0xFDFF)
            or (0xFE70 <= code <= 0xFEFF)
            or ch in ("۔", "،", "؟", "؛", "«", "»", "ـ")
        )

    def _fix_doubled_text(self, text: str) -> str:
        """Undo doubled characters some PDF renderers produce, e.g.
        'CCoonnttrraacctt' -> 'Contract'."""
        fixed_lines = []
        for line in text.splitlines():
            if not line.strip():
                fixed_lines.append(line)
                continue
            fixed_lines.append(self._fix_doubled_line(line))
        return "\n".join(fixed_lines)

    def _fix_doubled_line(self, line: str) -> str:
        tokens: list[str] = []
        current: list[str] = []
        for ch in line:
            if ch.isspace():
                if current:
                    tokens.append("".join(current))
                    current = []
                tokens.append(ch)
            else:
                current.append(ch)
        if current:
            tokens.append("".join(current))
        return "".join(self._fix_doubled_token(token) for token in tokens)

    def _fix_doubled_token(self, token: str) -> str:
        if len(token) <= 1 or token.isspace():
            return token

        length = len(token)
        if length >= 4 and length % 2 == 0 and all(
            token[idx] == token[idx + 1] for idx in range(0, length, 2)
        ):
            return token[::2]

        duplicate_pairs = sum(1 for idx in range(length - 1) if token[idx] == token[idx + 1])
        if (length - 1) > 0 and duplicate_pairs / (length - 1) > 0.5:
            result = []
            idx = 0
            while idx < length:
                result.append(token[idx])
                if idx + 1 < length and token[idx] == token[idx + 1]:
                    idx += 2
                else:
                    idx += 1
            return "".join(result)

        return token

    def _fix_arabic_reversed(self, text: str) -> str:
        """Reverse Arabic runs stored in visual (LTR) order back to logical
        (RTL) order."""
        fixed_lines = [self._fix_arabic_reversed_line(line) for line in text.splitlines()]
        return "\n".join(fixed_lines)

    def _fix_arabic_reversed_line(self, line: str) -> str:
        chars = list(line)
        length = len(chars)
        idx = 0
        while idx < length:
            if not self.is_arabic_char(chars[idx]):
                idx += 1
                continue
            run_end = idx
            while run_end < length:
                if self.is_arabic_char(chars[run_end]):
                    run_end += 1
                elif chars[run_end] == " " and run_end + 1 < length and self.is_arabic_char(
                    chars[run_end + 1]
                ):
                    run_end += 1
                else:
                    break
            chars[idx:run_end] = chars[idx:run_end][::-1]
            idx = run_end
        return "".join(chars)
