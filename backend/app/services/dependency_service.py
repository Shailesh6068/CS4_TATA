import os
import re
from typing import Dict, List, Any
import networkx as nx

class DependencyService:
    """Analyzes module, include, and import relationships and detects circular dependencies."""

    def build_dependency_graph(self, files: Dict[str, str]) -> Dict[str, Any]:
        """
        Takes a dict of {relative_path: code_content} and builds a directed graph of relationships.
        """
        graph = nx.DiGraph()

        # Add nodes
        for file_path in files.keys():
            graph.add_node(file_path, file_name=os.path.basename(file_path))

        include_re = re.compile(r'^\s*#include\s+[<"]([^>"]+)[>"]')
        import_re = re.compile(r'^\s*(?:from\s+([a-zA-Z0-9_.]+)\s+import|import\s+([a-zA-Z0-9_.]+))')

        edges = []
        for src_path, content in files.items():
            ext = os.path.splitext(src_path)[1].lower()
            lines = content.splitlines()

            if ext in (".c", ".cpp", ".cc", ".h", ".hpp"):
                for line in lines:
                    m = include_re.match(line)
                    if m:
                        inc_target = m.group(1)
                        # Match with known project files
                        for candidate in files.keys():
                            if candidate.endswith(inc_target) or os.path.basename(candidate) == inc_target:
                                if candidate != src_path:
                                    graph.add_edge(src_path, candidate, type="include")
                                    edges.append({"source": src_path, "target": candidate, "label": "includes"})
                                break

            elif ext == ".py":
                for line in lines:
                    m = import_re.match(line)
                    if m:
                        module_target = m.group(1) or m.group(2)
                        mod_base = module_target.split(".")[0]
                        for candidate in files.keys():
                            cand_name = os.path.splitext(os.path.basename(candidate))[0]
                            if cand_name == mod_base and candidate != src_path:
                                graph.add_edge(src_path, candidate, type="import")
                                edges.append({"source": src_path, "target": candidate, "label": "imports"})
                                break

        # Detect circular dependencies
        try:
            cycles = list(nx.simple_cycles(graph))
        except Exception:
            cycles = []

        nodes_list = []
        for n, data in graph.nodes(data=True):
            in_degree = graph.in_degree(n)
            out_degree = graph.out_degree(n)
            nodes_list.append({
                "id": n,
                "label": os.path.basename(n),
                "in_degree": in_degree,
                "out_degree": out_degree,
                "is_leaf": out_degree == 0,
                "is_root": in_degree == 0
            })

        return {
            "nodes": nodes_list,
            "edges": edges,
            "has_cycles": len(cycles) > 0,
            "circular_dependencies": cycles,
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges()
        }

dependency_service = DependencyService()
