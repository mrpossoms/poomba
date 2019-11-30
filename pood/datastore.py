import os
import random
import string
from pathlib import Path
from PIL import Image


class DataStore:
    class FetchOperation:
        def __init__(self, data_store, classification):
            self.ds = data_store
            self.classification = classification
            self.example_paths = []

        def all(self):
            files = os.listdir('{}/{}'.format(self.ds.base_path, self.classification))
            for path, file in zip([str(self.ds.base_path)] * len(files), files):
                self.example_paths += [ path + '/' + file ]

            return self.example_paths

        def minibatch(self, size=100):
            if len(self.example_paths) == 0:
                self.mini_idx = 0
                all()

            batch = self.example_paths[self.mini_idx:self.minibatch_idx + size]
            self.minibatch_idx += size

            return batch

    class StoreOperation:
        def __init__(self, data_store, classification):
            self.ds = data_store
            self.classification = classification
            Path('{}/{}'.format(str(data_store.base_path), classification))\
                .mkdir(mode=0o777, parents=True, exist_ok=True)

        def tile(self, img, tiles=10, size=(64, 64)):
            for _ in range(tiles):
                x, y = random.randrange(0, img.width - size[0]), random.randrange(0, img.width - size[0])
                self._store(img.crop((x, y, x + size[0], y + size[1])))

        def _store(self, img):
            name = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
            img.save('{}/{}/{}.png'.format(self.ds.base_path, self.classification, name))

    def __init__(self, base_path=''):
        self.base_path = Path(base_path)
        self.base_path.mkdir(mode=0o777, parents=True, exist_ok=True)

    def store(self, classification):
        return self.StoreOperation(self, classification)

    def fetch(self, classification):
        return self.FetchOperation(self, classification)


if __name__ == '__main__':
    import numpy as np

    img_arr = (np.random.random((128, 128, 3)) * 255).astype(np.uint8)
    img = Image.fromarray(img_arr)

    def rm_tree(pth):
        pth = Path(pth)
        for child in pth.glob('*'):
            if child.is_file():
                child.unlink()
            else:
                rm_tree(child)
        pth.rmdir()

    rm_tree(Path('/tmp/ds'))

    ds = DataStore('/tmp/ds')
    ds.store('random').tile(img, tiles=10)

    assert(ds.base_path.exists())
    assert(len(ds.fetch('random').all()) == 10)

    print('ALL PASS')