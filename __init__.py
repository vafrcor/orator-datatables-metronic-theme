# By Vinsensius Angelo (https://github.com/vafrcor/orator-datatables)

# This package inspired by https://pypi.org/project/datatables/
# and using `orator` ORM implementation
from collections import defaultdict, namedtuple
import re
import inspect
import math

# BOOLEAN_FIELDS = (
#     "search.regex", "searchable", "orderable", "regex"
# )

BOOLEAN_FIELDS = (
    "filterable", "sortable"
)


DataColumn = namedtuple("DataColumn", ("name", "model_name", "filter"))


class DataTablesError(ValueError):
    pass


class DataTableMetronic(object):
    def __init__(self, params, model, query, columns):
        self.params = params
        self.model = model
        self.query = query
        self.data = {}
        self.columns = []
        self.columns_dict = {}
        self.search_func = lambda qs, s: qs

        for col in columns:
            name, model_name, filter_func = None, None, None

            if isinstance(col, DataColumn):
                self.columns.append(col)
                continue
            elif isinstance(col, tuple):
                # col is either 1. (name, model_name), 2. (name, filter) or 3. (name, model_name, filter)
                if len(col) == 3:
                    name, model_name, filter_func = col
                elif len(col) == 2:
                    # Work out the second argument. If it is a function then it's type 2, else it is type 1.
                    if callable(col[1]):
                        name, filter_func = col
                        model_name = name
                    else:
                        name, model_name = col
                else:
                    raise ValueError("Columns must be a tuple of 2 to 3 elements")
            else:
                # It's just a string
                name, model_name = col, col

            d = DataColumn(name=name, model_name=model_name, filter=filter_func)
            self.columns.append(d)
            self.columns_dict[d.name] = d

        # querying relationship (not-supported yet)
        """
        for column in (col for col in self.columns if "." in col.model_name):
            self.query = self.query.join(column.model_name.split(".")[0])
        """

    def query_into_dict(self, key_start):
        returner = defaultdict(dict)

        # Matches columns[number][key] with an [optional_value] on the end
        pattern = "{}(?:\[(\d+)\])?\[(\w+)\](?:\[(\w+)\])?".format(key_start)

        columns = (param for param in self.params if re.match(pattern, param))

        for param in columns:

            column_id, key, optional_subkey = re.search(pattern, param).groups()

            if column_id is None:
                returner[key] = self.coerce_value(key, self.params[param])
            elif optional_subkey is None:
                returner[int(column_id)][key] = self.coerce_value(key, self.params[param])
            else:
                # Oh baby a triple
                subdict = returner[int(column_id)].setdefault(key, {})
                subdict[optional_subkey] = self.coerce_value("{}.{}".format(key, optional_subkey),
                                                             self.params[param])

        return dict(returner)

    @staticmethod
    def coerce_value(key, value):
        try:
            return int(value)
        except ValueError:
            if key in BOOLEAN_FIELDS:
                return value == "true"

        return value

    def get_integer_param(self, param_name):
        if param_name not in self.params:
            raise DataTablesError("Parameter {} is missing".format(param_name))

        try:
            return int(self.params[param_name])
        except ValueError:
            raise DataTablesError("Parameter {} is invalid".format(param_name))

    def add_data(self, **kwargs):
        self.data.update(**kwargs)

    def json(self):
        try:
            return self._json()
        except DataTablesError as e:
            return {
                "error": str(e)
            }

    def get_column(self, column):
        if "." in column.model_name:
            column_path = column.model_name.split(".")
            relationship = getattr(self.model, column_path[0])
            model_column = getattr(relationship.property.mapper.entity, column_path[1])
        else:
            model_column = getattr(self.model, column.model_name)

        return model_column

    def searchable(self, func):
        self.search_func = func

    def _json(self):
        # draw = self.get_integer_param("draw")
        # start = self.get_integer_param("start")
        # length = self.get_integer_param("length")

        pagination= self.query_into_dict("pagination")
        page = int(pagination.get("page", 1))
        pages = 1;
        length = int(pagination.get("perpage", -1))
        
        columns = self.query_into_dict("columns")
        # ordering = self.query_into_dict("order")
        ordering = self.query_into_dict("sort")

        # search = self.query_into_dict("search")
        search = self.query_into_dict("query")

        query = self.query
        total_records = query.count()

        
        # if callable(self.search_func) and search.get("value", None):
        #     query = self.search_func(query, str(search["value"]))

        if callable(self.search_func) and search.get("q", None):
            query = self.search_func(query, str(search["q"]))

            del search["q"]

        """
        for order in ordering.values():
            direction, column = order["dir"], order["column"]

            if column not in columns:
                raise DataTablesError("Cannot order {}: column not found".format(column))

            if not columns[column]["orderable"]:
                continue

            column_name = columns[column]["data"]
            column = self.columns_dict[column_name]

            # model_column = self.get_column(column)

            # if isinstance(model_column, property):
            #     raise DataTablesError("Cannot order by column {} as it is a property".format(column.model_name))

            # query = query.order_by(model_column.desc() if direction == "desc" else model_column.asc())
            query= query.order_by(column_name, direction)
        """

        order_column= None
        order_direction= None
        if ordering.get("field", None) is not None:
            order_column= ordering.get("field", None)
            order_direction= ordering.get("sort", "asc")
            
            # if column not in columns:
            if order_column not in self.columns_dict:
                raise DataTablesError("Cannot order {}: column not found".format(order_column))

            query= query.order_by(order_column, order_direction)


        filtered_records = query.count()
        

        if (length > 0):
            pages  = math.ceil(filtered_records / length)
            # handle if pagination['page'] value is "-1"
            page   = max([page, 1])
            # get last page when pagination['page'] > filtered_records
            page   = min([page, pages]); 
        
        skip = (page - 1) * length;

        # query = query.slice(start, start + length)
        query = query.offset(skip).limit(length)

        # return {
        #     "draw": draw,
        #     "recordsTotal": total_records,
        #     "recordsFiltered": filtered_records,
        #     "data": [
        #         # self.output_instance(instance) for instance in query.all()
        #         self.output_instance(instance) for instance in query.get()
        #     ]
        # }


        return {
            "meta":{
                "page": page,
                "pages": pages,
                "perpage": length,
                "total": filtered_records,
                "total_alldata": total_records,
                "sort": order_column,
                "field": order_direction
            },
            "data": [
                # self.output_instance(instance) for instance in query.all()
                self.output_instance(instance) for instance in query.get()
            ]
        }

    def output_instance(self, instance):
        returner = {
            key.name: self.get_value(key, instance) for key in self.columns
        }

        if self.data:
            returner["DT_RowData"] = {
                k: v(instance) for k, v in self.data.items()
            }

        return returner

    def get_value(self, key, instance):
        attr = key.model_name
        if "." in attr:
            subkey, attr = attr.split(".", 1)
            instance = getattr(instance, subkey)

        if key.filter is not None:
            r = key.filter(instance)
        else:
            r = getattr(instance, attr)

        return r() if inspect.isroutine(r) else r