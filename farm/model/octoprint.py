from octorest import OctoRest

from contextlib import contextmanager
from urllib import parse as urlparse
from time import sleep

from requests_toolbelt.multipart import encoder


class Octoprint(OctoRest):
    def __init__(self, url, api_key, timeout=None, session=None):
        self.timeout = timeout
        super().__init__(url=url, apikey=api_key, session=session)

    def _get(self, path, params=None):
        url = urlparse.urljoin(self.url, path)
        response = self.session.get(url, params=params, timeout=self.timeout)
        self._check_response(response)

        return response.json()
    
    def _post(self, path, data=None, files=None, json=None, ret=True):
        url = urlparse.urljoin(self.url, path)
        if not files:
            response = self.session.post(url, data=data, files=files, json=json)
        else:
            data.update({
                'file': files['file'],
            })
            file_data = encoder.MultipartEncoder(data)

            headers = {}
            headers.update(self.session.headers)
            headers.update({'Content-Type': file_data.content_type})

            response = self.session.post(url, headers=headers, data=file_data, json=json)

        self._check_response(response)
        if ret:
            return response.json()
    
    def new_folder(self, folder_name, location='local'):
        """Upload file or create folder
        http://docs.octoprint.org/en/master/api/files.html#upload-file-or-create-folder

        To create a new folder, the request body must at least contain the foldername
        form field, specifying the name of the new folder. Note that folder creation
        is currently only supported on the local file system.
        """
        data = {
            'foldername': folder_name,
        }
        return self._post('/api/files/{}'.format(location), data=data)



    def upload(self, file, *, location='local',
               select=False, print=False, userdata=None, path=None):
        """Upload file or create folder
        http://docs.octoprint.org/en/master/api/files.html#upload-file-or-create-folder

        Upload a given file
        It can be a path or a tuple with a filename and a file-like object
        """
        with self._file_tuple(file) as file_tuple:
            files = {'file': file_tuple}
            data = {
                'select': str(select).lower(),
                'print': str(print).lower()
            }
            if userdata:
                data['userdata'] = userdata
            if path:
                data['path'] = path

            return self._post('/api/files/{}'.format(location),
                              files=files, data=data)