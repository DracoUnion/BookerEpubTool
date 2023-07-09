import zipfile
from io import BytesIO
import re
import subprocess as subp
from os import path

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

def convert_to_epub(fname):
    nfname = re.sub(r'\.\w+$', '', fname) + '.epub'
    print(f'{fname} => {nfname}')
    subp.Popen(f'ebook-convert "{fname}" "{nfname}"', 
        shell=True, stdin=subp.PIPE, stdout=subp.PIPE).communicate()
    if not path.exists(nfname):
        raise FileNotFoundError(f'{nfname} not found')
    return nfname