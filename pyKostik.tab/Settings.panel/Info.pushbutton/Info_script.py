import os

from pyrevit import script
from pyrevit.versionmgr import updater
from pyrevit.coreutils import git


class RemoteRepository(object):
    """Wrapper for LibGit2Sharp Remote Repository."""

    def __init__(self, repository):
        self._repo = repository

    @property
    def repo(self):
        return self._repo

    @property
    def name(self):
        return str(self.repo.Name)

    @property
    def url(self):
        return str(self.repo.Url)


class PathWrap(object):

    def __init__(self, path):
        # type: (str) -> None
        self._path = os.path.normpath(path)
        self._parts = self._path.split(os.sep)

    def __str__(self):
        return self._path

    def last_part_with_suffix(self, suffix):
        # type: (str) -> int
        """Gets index of the last part that ends with specified text"""

        indexes = self.parts_with_suffix(suffix)

        if not indexes:
            raise ValueError(
                'There is no part in "{}" that ends with `{}`'
                .format(self._path, suffix)
            )
        return indexes[-1]

    def parts_with_suffix(self, suffix):
        # type: (str) -> list[int]
        """Gets indexes of the parts that end with specified text"""
        indexes = []
        for index, part in enumerate(self._parts):
            if part.endswith(suffix):
                indexes.append(index)
        return indexes

    def cut_at(self, part_index):
        # type: (int) -> os.path
        drive, tail = os.path.splitdrive(self._path)
        drive_path = os.path.join(drive, os.sep)

        cut_path = drive_path
        for part in self._parts[:part_index]:
            cut_path = os.path.join(cut_path, part)
        return cut_path


def get_local_repo_path(dir_path):
    # type: (str) -> str
    return git.libgit.Repository.Discover(dir_path)


def get_repo_info(repo_path):
    """Gets `pyrevit.coreutils.git.RepoInfo` object"""
    return git.get_repo(repo_path)


def get_remotes(repo_info):
    # type: (git.RepoInfo) -> list[RemoteRepository]
    return [RemoteRepository(repo) for repo in repo_info.repo.Network.Remotes]


def get_origin_url(remotes):
    # type: (list[RemoteRepository]) -> str
    for remote in remotes:
        if remote.name == 'origin':
            return remote.url


def get_update_status(repo_info):
    # type: (git.RepoInfo) -> str
    if updater.has_pending_updates(repo_info):
        return (
            ':cross_mark: You are not using the latest version.\n'
            'follow these instructions to update:\n'
            'https://github.com/nodatasheet/pyKostik#update'
        )
    return ':white_heavy_check_mark: Congrats! You are up to date!'


path_wrap = PathWrap(__file__)
cut_index = path_wrap.last_part_with_suffix('.extension') + 1
extension_path = path_wrap.cut_at(cut_index)

extension_repo_path = get_local_repo_path(extension_path)
extension_repo_info = get_repo_info(extension_repo_path)
extension_remotes = get_remotes(extension_repo_info)

extension_name = extension_repo_info.name
extension_branch = extension_repo_info.branch
extension_url = get_origin_url(extension_remotes)
update_status = get_update_status(extension_repo_info)

output = script.get_output()
output.print_md(
    'Extension name: {} (branch-{})'.format(extension_name, extension_branch))
output.print_md('Extension location: {}'.format(extension_path))
output.print_md('Extension site: [{0}]({0})'.format(extension_url))
output.print_md('Updates status: {}'.format(update_status))
