<html>
<head>
    <style type="text/css">
        ${css}
    </style>
</head>
<body>    
    <h1><br /></h1>
    <span class="title">${_("LISTADO DE CHEQUES DE TERCEROS")} </span>
    <br/>
    <table class="list_table"  width="90%">
        <thead><tr><th>${_("Fecha")}</th><th>${_("Numero")}</th><th>${_("Numero Interno")}</th><th>${_("Nombre del Banco")}</th><th>${_("Nombre del Cliente")}</th><th >${_("Estado")}</th><th>${_("Total")}</th></tr></thead>
        %for line in objects :
        <tbody>
        <tr><td>${line.date}</td><td>${line.number}</td><td>${line.sequence_number}</td><td>${line.bank_id.name or ''}</td><td>${line.source_partner_id.name or ''}</td><td>${line.state}</td><td>${line.amount or 0.00}</td></tr>
        %endfor
        </tbody>
    </table>
</body>
</html>
