import zipfile
from io import BytesIO

def read_zip(fname):
    bio = BytesIO(open(fname, 'rb').read())
    zip = zipfile.open(bio, 'r')
    fdict = {n:zip.read(n) for n in zip.namelist()}
    zip.close()
    return fdict

def write_zip(fname, fdict):
    bio = BytesIO()
    zip = zipfile.open(bio, 'w')
    for name, data in fdict.items():
        zip.writestr(name, data)
    zip.close()
    open(fname, 'wb').write(bio.getvalue())
