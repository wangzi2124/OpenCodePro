import inspect
import os


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, func):
        self._tools[func.__name__] = func
        return func

    def get(self, name):
        return self._tools.get(name)

    def list_tools(self):
        result = []
        for name, func in self._tools.items():
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""
            params = {}
            for param_name, param in sig.parameters.items():
                params[param_name] = {
                    "required": param.default == inspect.Parameter.empty,
                    "description": "",
                }
            result.append({
                "name": name,
                "description": doc.split("\n")[0] if doc else "",
                "parameters": params,
            })
        return result

    def get_tool_definitions(self):
        definitions = {}
        for name, func in self._tools.items():
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""
            params = {}
            for param_name, param in sig.parameters.items():
                params[param_name] = {
                    "type": "string",
                    "required": param.default == inspect.Parameter.empty,
                    "description": "",
                }
            definitions[name] = {
                "name": name,
                "description": doc,
                "parameters": params,
            }
        return definitions


def get_file_list(directory):
    result = []
    for root, dirs, files in os.walk(directory):
        level = root.replace(directory, "").count(os.sep)
        if level > 3:
            continue
        indent = "  " * level
        result.append(f"{indent}{os.path.basename(root)}/")
        for f in files:
            result.append(f"{indent}  {f}")
        if len(result) > 100:
            break
    return "\n".join(result)
