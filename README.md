# orator-datatables
jQuery Datatables server-side-processing wrapper for Python using [Orator ORM](http://orator-orm.com/).

This project was inspired by [SQLAlchemy-Datatables](https://github.com/orf/datatables/)


Installation
------------

The package is available on `PyPI <https://pypi.python.org/pypi/orator-datatables>`_ and is tested on Python 2.7 to 3.6

```bash
    pip install orator-datatables
```

Usage
-----

Using Datatables is simple. Construct a DataTable instance by passing it your request parameters (or another dict-like object), your model class, a base query and a set of columns. The columns list can contain simple strings which are column names, or tuples containing (datatable_name, model_name), (datatable_name, model_name, filter_function) or (datatable_name, filter_function).


Example
-------

**model.py**

```python
from orator import DatabaseManager, Model, Schema

config = {
	'default': 'mysql',
    'mysql': {
        'driver': 'mysql',
        'host': 'localhost',
        'database': 'database',
        'user': 'root',
        'password': 'root',
        'prefix': ''
    }
}

db = DatabaseManager(config)

# comment line below to enable query log
# db.connection().enable_query_log()

Model.set_connection_resolver(db)
schema = Schema(db)


class User(Model):
	__tablename__ = 'users'
	__primary_key__ = 'id'
	__columns__ = ['id','username','full_name','created_at','updated_at']
	
	@classmethod
	def getColumns(self):
		return self.__columns__
```

**app.py (example on Flask Framework)**

```python
from flask import Flask, request, jsonify, render_template
from orator_datatable import DataTable
import datetime, json

from model import User

app = Flask(__name__)

def json_datetime_converter(o):
 	if isinstance(o, datetime.datetime):
   		return o.__str__()

def json_response_converter(data={}):
	data= json.dumps(data, default=json_datetime_converter)
 	data= json.loads(data)
	return data

def datatable_search_orator(queryset, user_input):
	# write additional Orator Query builder here
	# queryset= queryset.where('username','like','%'+str(user_input)+'%')
	return queryset

@app.route("/")
def index():
    return render_template('datatables.html')
    
@app.route("/datatables")
def datatable():
    raw_args=request.query_string
   	args=request.args.to_dict()
   	UserQuery= User.where_raw('id > -1')
   	columns= User.getColumns()
   	table = DataTable(request.args.to_dict(), User, UserQuery, columns)
    
    # enable search 
   	table.searchable(lambda queryset, user_input: datatable_search_orator(queryset, user_input))

   	# return as dictionary
  	results= table.json()
  	# convert datetime.datetime entry to string
 	results= json_response_converter(results)

 	# send result
 	return app.make_response(jsonify(results), 200)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8888)

# How to Test:
# - Via terminal `python app.py`
# - View via browser http://127.0.0.1:8888/
```

**templates/datatables.html**

```html
<!-- Add jQuery library and jQuery datatables plugin here -->

<!-- table html -->
<table class="table" id="table">
	<thead>
  		<tr>
         	<th>Id</th>
         	<th>User name</th>
        	<th>Address</th>
      	</tr>
 	</thead>
  	<tbody>
 	</tbody>
</table>

<!-- load jQuery Datatable -->
<script type="text/javascript">
jQuery("#table").dataTable({
	serverSide: true,
 	processing: true,
 	ajax: "/datatables",
 	columns: [
		{ data: "id" },
		{ data: "username" },
   		{ data: "full_name" },
   		{ data: "created_at" },
   		{ data: "updated_at" }
 	]
});
</script>
```