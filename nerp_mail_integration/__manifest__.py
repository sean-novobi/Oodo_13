{
    'name': "Mail Integration",
    'summary': "Lead Generation from Emails",
    'description': """
        Convert incoming emails to lead
""",
    'author': "Novobi LLC",
    'category': '',
    'version': '13.0.0',
    'depends': ['mail',
                'fetchmail',
                'crm',
                'base'
                ],
    'data': [
        'data/fetch_sentmail.xml',
        'data/mail_data.xml',
        'views/fetchmail_views.xml',
    ],
    'demo': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}

