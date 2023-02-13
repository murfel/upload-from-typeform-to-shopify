from typing import List

import requests
import time
import shutil
import json


class BackgroundRemover:
    params = {
        'lang': 'en',
        'convert_to': 'image-backgroundremover',
        'ocr': False
    }

    api_url = 'https://api.backgroundremover.app/v1/convert/'
    results_url = 'https://api.backgroundremover.app/v1/results/'

    def __init__(self, token):
        self.headers = {'Authorization': token}

    def remove_background(self, file_bytes_list: List[bytes]):
        return BackgroundRemover._get_results(
            BackgroundRemover._convert_files(
                BackgroundRemover.api_url, BackgroundRemover.params, self.headers, file_bytes_list))

    @staticmethod
    def _download_file(url, local_filename, save_locally=False):
        r = requests.get("https://api.backgroundremover.app/%s" % url, stream=True)

        if save_locally:
            with open(local_filename, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            return local_filename

        return r.raw.data

    @staticmethod
    def _convert_files(api_url, params, headers, file_bytes_list):
        r = requests.post(
            url=api_url,
            files=[('files', file) for file in file_bytes_list],
            data=params,
            headers=headers
        )
        return r.json()

    @staticmethod
    def _get_results(params):
        finished = False
        data = None
        while not finished:
            r = requests.post(
                url=BackgroundRemover.results_url,
                data=params
            )
            data = r.json()
            finished = data.get('finished')
            if not finished:
                time.sleep(5)

        file_bytes_list_no_background = []
        for f in data.get('files'):
            print(f.get('url'))
            file_bytes = BackgroundRemover._download_file("%s" % f.get('url'), "%s" % f.get('filename'))
            file_bytes_list_no_background.append(file_bytes)
        return file_bytes_list_no_background
