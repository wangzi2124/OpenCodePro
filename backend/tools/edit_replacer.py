import re
from typing import Generator, Optional


def levenshtein(a: str, b: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if not a or not b:
        return max(len(a), len(b))

    matrix = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]

    for i in range(len(a) + 1):
        matrix[i][0] = i
    for j in range(len(b) + 1):
        matrix[0][j] = j

    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            matrix[i][j] = min(
                matrix[i-1][j] + 1,
                matrix[i][j-1] + 1,
                matrix[i-1][j-1] + cost
            )

    return matrix[len(a)][len(b)]


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    dist = levenshtein(a, b)
    max_len = max(len(a), len(b))
    return 1 - (dist / max_len)


class Replacer:
    """Base class for string replacers."""

    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        """Find exact matches in content."""
        if find in content:
            yield find


class SimpleReplacer(Replacer):
    """Simple exact match replacer."""

    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        if find in content:
            yield find


class LineTrimmedReplacer(Replacer):
    """Match with leading/trailing whitespace trimmed."""

    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        lines = content.split("\n")
        search_lines = find.split("\n")

        # Remove trailing empty line
        if search_lines and search_lines[-1] == "":
            search_lines = search_lines[:-1]

        for i in range(len(lines) - len(search_lines) + 1):
            matches = True
            for j in range(len(search_lines)):
                if lines[i + j].strip() != search_lines[j].strip():
                    matches = False
                    break

            if matches:
                start = sum(len(lines[k]) + 1 for k in range(i))
                end = start + sum(len(lines[i + j]) for j in range(len(search_lines))) + len(search_lines) - 1
                yield content[start:end]


class BlockAnchorReplacer(Replacer):
    """Match using first and last line as anchors."""

    SINGLE_THRESHOLD = 0.0
    MULTIPLE_THRESHOLD = 0.3

    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        lines = content.split("\n")
        search_lines = find.split("\n")

        if len(search_lines) < 3:
            return

        # Remove trailing empty line
        if search_lines and search_lines[-1] == "":
            search_lines = search_lines[:-1]

        first_search = search_lines[0].strip()
        last_search = search_lines[-1].strip()

        # Find candidates
        candidates = []
        for i in range(len(lines)):
            if lines[i].strip() != first_search:
                continue

            for j in range(i + 2, len(lines)):
                if lines[j].strip() == last_search:
                    candidates.append((i, j))
                    break

        if not candidates:
            return

        # Single candidate
        if len(candidates) == 1:
            start_line, end_line = candidates[0]
            if start_line == end_line:
                yield lines[start_line]
            else:
                start = sum(len(lines[k]) + 1 for k in range(start_line))
                end = start + sum(len(lines[k]) for k in range(start_line, end_line + 1)) + (end_line - start_line)
                yield content[start:end]
            return

        # Multiple candidates - find best match
        best_match = None
        best_similarity = -1

        for start_line, end_line in candidates:
            search_len = len(search_lines)
            actual_len = end_line - start_line + 1

            sim = 0.0
            check_count = 0
            for j in range(1, min(search_len - 1, actual_len - 1)):
                orig = lines[start_line + j].strip()
                srch = search_lines[j].strip()
                if orig and srch:
                    sim += similarity(orig, srch)
                    check_count += 1

            if check_count > 0:
                sim /= check_count

            if sim > best_similarity:
                best_similarity = sim
                best_match = (start_line, end_line)

        if best_match and best_similarity >= BlockAnchorReplacer.MULTIPLE_THRESHOLD:
            start_line, end_line = best_match[0], best_match[1]
            if start_line == end_line:
                yield lines[start_line]
            else:
                start = sum(len(lines[k]) + 1 for k in range(start_line))
                end = start + sum(len(lines[k]) for k in range(start_line, end_line + 1)) + (end_line - start_line)
                yield content[start:end]


class WhitespaceNormalizedReplacer(Replacer):
    """Match with whitespace normalized."""

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        normalized_find = WhitespaceNormalizedReplacer.normalize(find)
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if WhitespaceNormalizedReplacer.normalize(line) == normalized_find:
                yield line
                continue

            # Check for substring matches
            normalized_line = WhitespaceNormalizedReplacer.normalize(line)
            if normalized_find in normalized_line:
                words = find.strip().split()
                if words:
                    pattern = "|".join(re.escape(w) for w in words)
                    match = re.search(pattern, line)
                    if match:
                        yield match.group()


class IndentationFlexibleReplacer(Replacer):
    """Match with flexible indentation."""

    @staticmethod
    def remove_indentation(text: str) -> str:
        lines = text.split("\n")
        non_empty = [l for l in lines if l.strip()]
        if not non_empty:
            return text

        min_indent = min(len(l) - len(l.lstrip()) for l in non_empty)
        return "\n".join(
            l if l.strip() else l
            for l in lines
        ).replace(" " * min_indent, "", 1) if min_indent > 0 else text

    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        normalized_find = IndentationFlexibleReplacer.remove_indentation(find)
        content_lines = content.split("\n")
        find_lines = find.split("\n")

        for i in range(len(content_lines) - len(find_lines) + 1):
            block = "\n".join(content_lines[i:i + len(find_lines)])
            if IndentationFlexibleReplacer.remove_indentation(block) == normalized_find:
                yield block


class EscapeNormalizedReplacer(Replacer):
    """Match with escape sequences normalized."""

    UNESCAPE_MAP = {
        r'\n': '\n',
        r'\t': '\t',
        r'\r': '\r',
        r"\'": "'",
        r'\"': '"',
        r'\\': '\\',
    }

    @staticmethod
    def unescape(text: str) -> str:
        for escaped, char in EscapeNormalizedReplacer.UNESCAPE_MAP.items():
            text = text.replace(escaped, char)
        return text

    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        unescaped_find = EscapeNormalizedReplacer.unescape(find)

        if unescaped_find in content:
            yield unescaped_find

        # Also check for escaped versions in content
        lines = content.split("\n")
        find_lines = unescaped_find.split("\n")

        for i in range(len(lines) - len(find_lines) + 1):
            block = "\n".join(lines[i:i + len(find_lines)])
            if EscapeNormalizedReplacer.unescape(block) == unescaped_find:
                yield block


class TrimmedBoundaryReplacer(Replacer):
    """Match with trimmed boundaries."""

    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        trimmed_find = find.strip()

        if trimmed_find == find:
            return

        if trimmed_find in content:
            yield trimmed_find

        lines = content.split("\n")
        find_lines = find.split("\n")

        for i in range(len(lines) - len(find_lines) + 1):
            block = "\n".join(lines[i:i + len(find_lines)])
            if block.strip() == trimmed_find:
                yield block


class ContextAwareReplacer(Replacer):
    """Match using context anchors (first and last line)."""

    @staticmethod
    def find_matches(content: str, find: str) -> Generator[str, None, None]:
        find_lines = find.split("\n")
        if len(find_lines) < 3:
            return

        if find_lines[-1] == "":
            find_lines = find_lines[:-1]

        content_lines = content.split("\n")
        first_line = find_lines[0].strip()
        last_line = find_lines[-1].strip()

        for i in range(len(content_lines)):
            if content_lines[i].strip() != first_line:
                continue

            for j in range(i + 2, len(content_lines)):
                if content_lines[j].strip() == last_line:
                    block_lines = content_lines[i:j + 1]
                    if len(block_lines) == len(find_lines):
                        matches = sum(
                            1 for k in range(1, len(block_lines) - 1)
                            if block_lines[k].strip() == find_lines[k].strip()
                        )
                        total = sum(1 for k in range(1, len(block_lines) - 1)
                                   if block_lines[k].strip() or find_lines[k].strip())

                        if total == 0 or matches / total >= 0.5:
                            yield "\n".join(block_lines)
                    break


def replace_content(content: str, old_string: str, new_string: str, replace_all: bool = False) -> tuple:
    """
    Try multiple replacers to find and replace content.
    Returns (new_content, diff) or raises error.
    """
    # First try exact match
    if old_string in content:
        first_idx = content.index(old_string)
        last_idx = content.rindex(old_string)
        
        if first_idx != last_idx and not replace_all:
            raise ValueError(
                f"Found multiple matches for oldString. "
                f"Provide more surrounding lines in oldString to identify the correct match."
            )
        
        if replace_all:
            new_content = content.replace(old_string, new_string)
            return new_content, _create_diff(content, new_content)
        
        new_content = content[:first_idx] + new_string + content[first_idx + len(old_string):]
        return new_content, _create_diff(content, new_content)

    # Try with whitespace normalization
    normalized_old = " ".join(old_string.split())
    if not normalized_old:
        raise ValueError("oldString not found in content")
        
    normalized_content = " ".join(content.split())
    if normalized_old in normalized_content:
        if replace_all:
            new_content = content.replace(old_string, new_string)
            return new_content, _create_diff(content, new_content)
        
        idx = normalized_content.index(normalized_old)
        orig_idx = 0
        count = 0
        while count < idx and orig_idx < len(content):
            if content[orig_idx] == ' ':
                count += 1
            orig_idx += 1
        new_content = content[:orig_idx] + new_string + content[orig_idx + len(old_string):]
        return new_content, _create_diff(content, new_content)

    raise ValueError("oldString not found in content")


def _create_diff(old: str, new: str) -> str:
    """Create a simple diff between old and new content."""
    old_lines = old.split("\n")
    new_lines = new.split("\n")

    diff_lines = []
    for i, (old_line, new_line) in enumerate(zip(old_lines, new_lines)):
        if old_line != new_line:
            diff_lines.append(f"- {old_line}" if old_line else f"+ {new_line}")
        else:
            diff_lines.append(f"  {old_line}")

    if len(new_lines) > len(old_lines):
        for line in new_lines[len(old_lines):]:
            diff_lines.append(f"+ {line}")

    return "\n".join(diff_lines)