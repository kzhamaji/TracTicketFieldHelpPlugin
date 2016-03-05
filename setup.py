from setuptools import setup

extra = {}

setup(
    name='TracTicketFieldHelpPlugin',
    #description='',
    #keywords='',
    #url='',
    version='0.1',
    #license='',
    #author='',
    #author_email='',
    #long_description="",
    packages=['ticketfieldhelp'],
    package_data={
        'ticketfieldhelp': [
            'htdocs/css/*.css', 'htdocs/css/themes/*.css',
            'htdocs/js/*.js',
        ]
    },
    entry_points={
        'trac.plugins': [
            'ticketfieldhelp.web_ui = ticketfieldhelp.web_ui',
        ]
    },
    **extra
)
