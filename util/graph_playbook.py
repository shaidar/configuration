#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from pathlib2 import Path
from pygraphviz import AGraph
import click
import yaml

click.disable_unicode_literals_warning = True

DEFAULT_ROLE_DIR = (Path(__file__).parent/'../playbooks/roles').resolve()

# List of application services
SERVICES = (
    'analytics_api',
    'certs',
    'ecommerce',
    'ecomworker',
    'edxapp',
    'elasticsearch',
    'forum',
    'insights',
    'memcache',
    'mongo',
    'mysql',
    'nginx',
    'notifier',
    'programs',
    'rabbitmq',
    'supervisor',
    'xqueue',
)

# DOT graph options
FONT_NAME = 'helvetica'

LABEL_SIZE = 20

LAYOUT = 'dot'

# DOT node options
OPTIONAL_SERVICE_COLOR = 'darkolivegreen1'

SERVICE_COLOR = 'cornflowerblue'

NODE_OPTIONS = dict(fontname=FONT_NAME)

# DOT edge options
EDGE_OPTIONS = dict(
    arrowsize=.5,
    dir='back',
    style='dashed',
)


class Role(object):
    """
    Ansible role.

    Attributes:
        name (str)
        is_optional (bool): If the role has a `when` conditional.
        dependencies (List[Role]): Immediately dependent roles.
    """

    def __init__(self, name, is_optional=False):
        """
        Init.

        Arguments:
            name (str)
            is_optional (bool)
        """
        self.name = name
        self.is_optional = is_optional
        self.dependencies = []

    def __str__(self):
        suffix = ' (optional)' if self.is_optional else ''
        return self.name + suffix

    @property
    def color(self):
        """
        str: Background color of this role in the graph.
        """
        color = 'transparent'
        if self.is_optional:
            color = OPTIONAL_SERVICE_COLOR
        elif self.is_service:
            color = SERVICE_COLOR
        return color

    @property
    def is_service(self):
        """
        bool: Is this role a service?
        """
        return self.name in SERVICES

    @property
    def style(self):
        """
        str: Fill style of this role in the graph.
        """
        if self.is_service:
            return 'filled'
        else:
            return ''


def _add_node(graph, node, **kwargs):
    """
    Add a node to the graph.

    **WARNING** The `graph` object is mutated by this function.

    The node will have default attributes from `NODE_OPTIONS`,
    overridable via `kwargs`.

    Arguments:
        graph (pygraphviz.AGraph)
        node (str)
        **kwargs (Any): Any valid node attributes.
    """
    options = NODE_OPTIONS.copy()
    options.update(kwargs)
    graph.add_node(node, **options)


def _generate_graph_label(text, font=FONT_NAME, size=LABEL_SIZE):
    """
    Generate graph label with specified font name and size.

    Arguments:
        text (str)
        font (str)
        size (Union[int, str])

    Returns:
        str
    """
    label = '<<FONT FACE="{}" POINT-SIZE="{}">{}</FONT>>'.format(
        font, size, text
    )
    return label


def _get_role_dependencies(role, role_dir):
    """
    Get immediate dependents for a role.

    Arguments:
        role (Role)
        role_dir (str): Directory where the Ansible roles are defined.

    Returns:
        List[Role]: Immediately dependent roles.
    """
    deps_file = Path(role_dir).joinpath(role.name, 'meta', 'main.yml')
    if not deps_file.exists():
        return []

    with deps_file.open() as f:
        meta = yaml.safe_load(f.read())
    if meta:
        deps = _parse_raw_list(meta.get('dependencies', []))
    else:
        deps = []
    return deps


def _graph_legend(graph):
    """
    Add legend to the graph.

    **WARNING** The `graph` object is mutated by this function.

    Arguments:
        graph (pygraphviz.AGraph)
    """
    for entry, color in (
            ('Service', SERVICE_COLOR),
            ('Optional Service', OPTIONAL_SERVICE_COLOR)
    ):
        _add_node(graph, entry, style='filled', fillcolor=color)


def _graph_role(graph, role, highlight_services=False):
    """
    Graph the role and its dependents.

    **WARNING** The `graph` object is mutated by this function.

    Arguments:
        graph (pygraphviz.AGraph)
        role (Role)
        highlight_services (bool): Should services defined in `SERVICES`
            be highlighted?
    """
    options = {}
    if highlight_services:
        options = dict(style=role.style, fillcolor=role.color)
    _add_node(graph, role.name, **options)

    for dep in role.dependencies:
        options = {}
        if highlight_services:
            options = dict(style=dep.style, fillcolor=dep.color)
        _add_node(graph, dep.name, **options)
        graph.add_edge(dep.name, role.name, **EDGE_OPTIONS)


def _parse_raw_list(raw_list):
    """
    Parse a list of roles into `Role` objects.

    Arguments:
        raw_list (List(Union([str, Dict[str, Any]])))

    Returns:
        List[Role]
    """
    roles = []

    for r in raw_list:
        if isinstance(r, basestring):
            roles.append(Role(r))
        if isinstance(r, dict):
            is_optional = False
            if 'when' in r:
                is_optional = True
            roles.append(Role(r['role'], is_optional))
    return roles


def echo_services(roles):
    """
    Echo out services contained contained in the list of roles.

    Arguments:
        roles (Dict(str, Role))
    """
    relevant_roles = (k for k in roles if k in SERVICES)
    for k in sorted(relevant_roles):
        click.echo(roles[k])


def expand_roles(raw_list, role_dir):
    """
    Generate a complete dictionary of all roles based on the input list.

    Arguments:
        raw_list (List(Union([str, Dict[str, Any]])))
        role_dir (str): Directory where the Ansible roles are defined.

    Returns:
        roles (Dict(str, Role))
    """
    role_list = _parse_raw_list(raw_list)
    roles = {}

    while role_list:
        role = role_list.pop(0)
        role.dependencies = _get_role_dependencies(role, role_dir)
        roles[role.name] = role
        role_list.extend(role.dependencies)

    return roles


def graph_roles(roles, outfile, playbook_path, highlight_services=False):
    """
    Generate a dependency graph based on roles provided.

    Arguments:
        roles (Dict(str, Role))
        outfile (str): Path to the output.
        playbook_path (str): Path to the playbook YAML file.
        highlight_services (bool): Whether services should be colored
            in the final output.
    """
    label = _generate_graph_label(Path(playbook_path).name)
    graph = AGraph(directed=True, label=label)

    if highlight_services:
        _graph_legend(graph)

    for k, role in roles.items():
        _graph_role(graph, role, highlight_services)

    graph.draw(outfile, prog=LAYOUT)


@click.command()
@click.argument('yaml-file', type=click.File('rb'))
@click.argument('output-file')
@click.option(
    '--role-dir',
    default=DEFAULT_ROLE_DIR.as_posix(),
    type=click.Path(exists=True),
    help="Directory where roles are stored. Default: {}".format(
        DEFAULT_ROLE_DIR
    )
)
@click.option(
    '--highlight-services', is_flag=True,
    help='Highlight predefined services in the graph.'
)
@click.option(
    '--list-services', is_flag=True,
    help='General a list of services contained in Ansible playbook.'
)
def cli(yaml_file, role_dir, output_file, highlight_services, list_services):
    """
    Graph role dependencies for an Ansible playbook.

    Output format will be determined by the extension specified.
    Not all may be available on every system depending on how
    Graphviz was built:

    ‘canon’, ‘cmap’, ‘cmapx’, ‘cmapx_np’, ‘dia’, ‘dot’, ‘fig’, ‘gd’, ‘gd2’,
    ‘gif’, ‘hpgl’, ‘imap’, ‘imap_np’, ‘ismap’, ‘jpe’, ‘jpeg’, ‘jpg’, ‘mif’,
    ‘mp’, ‘pcl’, ‘pdf’, ‘pic’, ‘plain’, ‘plain-ext’, ‘png’, ‘ps’, ‘ps2’, ‘svg’,
    ‘svgz’, ‘vml’, ‘vmlz’, ‘vrml’, ‘vtx’, ‘wbmp’, ‘xdot’, ‘xlib’

    \b
    Arguments:
        YAML_FILE: Path to the playbook YAML file.
        OUTPUT_FILE: Path to the generated graph output.
    """
    playbook = yaml.safe_load(yaml_file.read())
    role_list = playbook[0]['roles']
    roles = expand_roles(role_list, role_dir)
    graph_roles(roles, output_file, yaml_file.name, highlight_services)
    if list_services:
        echo_services(roles)


if __name__ == '__main__':
    cli()
