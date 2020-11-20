import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='sleepyjson',
    version='0.0.1',
    author='João D. Ferreira',
    author_email='jotomicron@gmail.com',
    description='Read from JSON files without having to keep everything in memory',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/jdferreira/sleepyjson',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
