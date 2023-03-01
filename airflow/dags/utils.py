import os
import yaml
import base64

class Utils:

    def get_yaml_dict(self,
                      file: str) -> dict:
        relative_file_path = self._get_relative_path()
        return self._get_open_file(f"{relative_file_path}/{file}.yaml")

    def string_to_base64(self, 
                         s: str) -> str:
        return str(base64.b64encode(s.encode('utf-8')).decode('utf-8'))

    @staticmethod
    def _get_relative_path() -> str:
        return os.path.dirname(os.path.realpath(__file__))

    @staticmethod
    def _get_open_file(file: str) -> dict:
        with open(file) as params_file:
            dic = yaml.load(params_file, Loader=YamlLoader)
        return dic

class SourceUtils(Utils):

    def get_yaml_dict(self,
                      source: str,
                      file: str) -> dict:
        relative_file_path = self._get_relative_path()
        return self._get_open_file(f"{relative_file_path}/{source}/{file}.yaml")


class SchemasUtils(Utils):

    def get_yaml_dict(self,
                      schema: str,
                      file: str) -> dict:
        relative_file_path = self._get_relative_path()
        return self._get_open_file(f"{relative_file_path}/schemas/{schema}/{file}.yaml")
    
    @staticmethod
    def get_dependency_key(external_dependency: list) -> str:
        return f"{external_dependency['dag_id']}_{external_dependency['task_id']}"

class YamlLoader(yaml.Loader):

    def __init__(self, stream):
        # register the tag handler
        self._stream = stream
        self.add_constructor('!concat', self._concat)
        super(YamlLoader, self).__init__(stream)

    @staticmethod
    def _concat(loader, node):
        seq = loader.construct_sequence(node)
        return ''.join([str(i) for i in seq])
