import os
import random
import secrets
import string
import numpy as np
from pathlib import Path
from PIL import Image


class DataStore:
    class FetchOperation:
        def __init__(self, data_store, classifications):
            self.ds = data_store
            self.classifications = classifications
            self.example_paths = []
            self.minibatch_idx = 0

        def all(self):
            max_class = 0
            for classification in self.classifications:
                base_path = '{}/{}'.format(self.ds.base_path, classification)
                file_count = len(os.listdir(base_path))
                if file_count > max_class:
                    max_class = file_count

            for classification in self.classifications:
                base_path = '{}/{}'.format(self.ds.base_path, classification)
                files = os.listdir(base_path)

                short = max_class - len(files)
                if short > 0:
                    for i in range(short):
                        files += [files[i]]

                for path, file in zip([base_path] * len(files), files):
                    if file[0] is '.': # skip hidden files
                        continue
                    self.example_paths += [ path + '/' + file ]

            return self

        def shuffle(self):
            random.shuffle(self.example_paths)
            return self

        def minibatch_count(self, batch_size=100):
            return len(self.example_paths) // batch_size

        def minibatch_next_paths(self, batch_size=100):
            return self.example_paths[self.minibatch_idx:self.minibatch_idx + batch_size]

        def minibatch(self, do_load=True, size=100, classes=None):
            if len(self.example_paths) == 0:
                self.all()
                self.shuffle()

            batch_paths = self.minibatch_next_paths(batch_size=size)
            self.minibatch_idx += size

            if do_load:
                X, Y = [], []
                for path in batch_paths:
                    img = Image.open(open(path, mode='rb'))
                    classification, _ = path.replace(str(self.ds.base_path) + '/', '').split('/')
                    img_arr = np.array(img.getdata()).reshape(img.height, img.width, 3)
                    img_arr = (img_arr - img_arr.min()) / (img_arr.max() - img_arr.min())
                    img_arr = (img_arr - 0.5) * 2.0
                    X += [img_arr]
                    try:
                        classification = int(classification)
                        if classes:
                            # emit a 1-hot vector
                            v = [0] * classes
                            v[classification] = 1
                            Y += [v]
                        else:
                            # emit a integer number class
                            Y += [classification]
                    except ValueError:
                            # emit raw string
                        Y += [classification]

                return X, Y
            else:
                return batch_paths, [self.classification] * len(batch_paths)

    class StoreOperation:
        def __init__(self, data_store, classification):
            self.ds = data_store
            self.classification = classification
            Path('{}/{}'.format(str(data_store.base_path), classification))\
                .mkdir(mode=0o777, parents=True, exist_ok=True)

        def tile(self, img, tiles=10, size=(64, 64)):
            for _ in range(tiles):
                x, y = random.randrange(0, img.width - size[0]), random.randrange(0, img.height - size[1])
                self._store(img.crop((x, y, x + size[0], y + size[1])))

        def _store(self, img):
            name = secrets.token_hex(2)
            img.save('{}/{}/{}.png'.format(self.ds.base_path, self.classification, name))

    def __init__(self, base_path=''):
        self.base_path = Path(base_path)
        self.base_path.mkdir(mode=0o777, parents=True, exist_ok=True)

    def store(self, classification):
        return self.StoreOperation(self, classification)

    def fetch(self, *classifications):
        return self.FetchOperation(self, classifications)


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
    ds.store(0).tile(img, tiles=10)
    ds.store(1).tile(img, tiles=10)

    assert(ds.base_path.exists())
    assert(len(ds.fetch(0).all()) == 10)

    X, Y = ds.fetch(0, 1).minibatch()

    assert(0 in Y)
    assert(1 in Y)

    print('ALL PASS')
