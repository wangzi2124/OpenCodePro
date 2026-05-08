import os
import json
import subprocess
from langchain.tools import tool as langchain_tool


@langchain_tool
def create_vite_project(directory: str, template: str = "react", name: str = None) -> str:
    """Create a new Vite project (react/vue/vanilla)."""
    project_name = name or os.path.basename(directory)
    src_dir = os.path.join(directory, "src")
    
    try:
        os.makedirs(src_dir, exist_ok=True)
    except Exception as e:
        return f"Error: {e}"
    
    pkg = {
        "name": project_name,
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"}
    }
    
    if "react" in template:
        pkg["dependencies"] = {"react": "^18.2.0", "react-dom": "^18.2.0"}
        pkg["devDependencies"] = {"@vitejs/plugin-react": "^4.2.1", "vite": "^5.1.0"}
        config = "import react from '@vitejs/plugin-react'\nexport default { plugins: [react()] }"
        ext = "jsx"
    elif "vue" in template:
        pkg["dependencies"] = {"vue": "^3.4.0"}
        pkg["devDependencies"] = {"@vitejs/plugin-vue": "^5.0.0", "vite": "^5.1.0"}
        config = "import vue from '@vitejs/plugin-vue'\nexport default { plugins: [vue()] }"
        ext = "vue"
    else:
        pkg["devDependencies"] = {"vite": "^5.1.0"}
        config = "export default {}"
        ext = "js"
    
    with open(os.path.join(directory, "package.json"), "w") as f:
        json.dump(pkg, f, indent=2)
    
    with open(os.path.join(directory, "vite.config.js"), "w") as f:
        f.write(config)
    
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'/><title>" + project_name + "</title></head><body><div id='root'></div><script type='module' src='/src/main." + ext + "'></script></body></html>"
    with open(os.path.join(directory, "index.html"), "w") as f:
        f.write(html)
    
    main = f"import React from 'react'\nimport ReactDOM from 'react-dom/client'\nimport App from './App.jsx'\nimport './index.css'\nReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>)"
    app = "import { useState } from 'react'\nfunction App() {\n  return (\n    <div><h1>Hello " + project_name + "!</h1></div>\n  )\n}\nexport default App"
    css = "* { margin: 0; padding: 0; box-sizing: border-box }\nbody { font-family: system-ui }"
    
    with open(os.path.join(src_dir, f"main.{ext}"), "w") as f:
        f.write(main if "react" in template else f"console.log('{project_name}')")
    with open(os.path.join(src_dir, f"App.{ext}"), "w") as f:
        f.write(app if "react" in template else f"console.log('{project_name}')")
    with open(os.path.join(src_dir, "index.css"), "w") as f:
        f.write(css)
    with open(os.path.join(directory, ".gitignore"), "w") as f:
        f.write("node_modules\ndist")
    
    return f"Created project at {directory}"


@langchain_tool
def install_dependencies(directory: str) -> str:
    """Install npm dependencies."""
    try:
        result = subprocess.run(["npm", "install"], cwd=directory, capture_output=True, text=True, timeout=180)
        return f"Installed in {directory}" if result.returncode == 0 else f"Failed: {result.stderr}"
    except Exception as e:
        return f"Error: {e}"


__all__ = ["create_vite_project", "install_dependencies"]