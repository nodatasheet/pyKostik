from pyrevit import DB, HOST_APP, forms, script

doc = HOST_APP.doc
active_view = HOST_APP.active_view

except_active_view = (lambda v: v.Id != active_view.Id)
views = forms.select_views(
    title='Select Views',
    filterfunc=except_active_view,
    multiple=True,
    button_name='Apply Visibility Properties to Views'
)  # type: list[DB.View]

if not views:
    script.exit()

transaction = DB.Transaction(doc, 'Apply Visibility Properties to Views')
transaction.Start()
try:
    for view in views:
        view.ApplyViewTemplateParameters(active_view)
    transaction.Commit()
except Exception as transaction_err:
    transaction.RollBack()
    forms.alert(
        msg=(
            'Can not apply visibility properties to this view:\n\n'
            '"{} ({})"\n\n'
            'Canceling.'
            .format(view.Name, view.ViewType)
        ),
        expanded=str(transaction_err)
    )
