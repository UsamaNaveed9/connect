from __future__ import unicode_literals
import frappe, json
from frappe import _
from erpnext.accounts.utils import get_balance_on
from frappe.utils import cint, fmt_money,flt,cstr, getdate,add_days
from frappe.utils.pdf import get_pdf
import frappe.permissions
from six.moves import range



@frappe.whitelist()
def cron_sync_order():
	orders = frappe.db.sql("""select name as 'order' from `tabConnector Sales Order` where sync=0 and retry_limit>0 order by creation desc limit 20""",as_dict=1)
	sync_sales_order_multiple_cron(orders)

@frappe.whitelist()
def sync_sales_order_multiple_cron(names):
	msg = ""
	for name in names:
		try:
			sync = frappe.db.get_value("Connector Sales Order",name.order,"sync")
			if int(sync) == 0:
				sync_sales_order(name.order)
			else:
				msg += "Order Alredy Synced {0}".format(name.order) + "<br/>"
		except Exception as e:
			msg += "Something Wrong in sync order {0}".format(name.order) + "<br/>"
			frappe.log_error(frappe.get_traceback())
	if not msg == "":
		frappe.msgprint(msg)

@frappe.whitelist()
def sync_sales_order_multiple(names):
	names = json.loads(names)
	msg = ""
	for name in names:
		try:
			sync = frappe.db.get_value("Connector Sales Order",name,"sync")
			
			if int(sync) == 0:
				sync_sales_order(name)
			else:
				msg += "Order Alredy Synced {0}".format(name) + "<br/>"
		except Exception as e:
			msg += "Something Wrong in sync order {0}".format(name) + "<br/>"
			frappe.log_error(frappe.get_traceback())
	if not msg == "":
		frappe.msgprint(msg)
			
@frappe.whitelist()
def sync_sales_order(order_no):
	if frappe.db.get_value('Connector Sales Order', order_no, 'sync'):
		frappe.throw('Order already synced')
		return False
	frappe.db.sql(''' update `tabConnector Sales Order` set retry_limit=%s where name=%s ''',( frappe.db.get_value('Connector Sales Order', order_no, 'retry_limit')-1, order_no) )
	# if frappe.db.get_value('Connector Sales Order', order_no, 'pos_profile'):
	# 	create_sales_invoice(order_no)
	# 	return True
	# else:
	create_sales_order(order_no)
	return True
	# return False

def create_sales_order(order_no):
	order_doc = frappe.get_doc("Connector Sales Order",order_no)
	if order_doc:
		customer_id = check_customer(order_doc)
		items = get_items(order_doc)
		taxes = get_taxes(order_doc)
		delivery_day = str(frappe.db.get_value("Connector Setting","Connector Setting","delivery_day"))
		submit_order = int(frappe.db.get_value("Connector Setting","Connector Setting","submit_order"))
		sales = get_sales_team(order_doc)
		so_doc = frappe.get_doc(dict(
			doctype = "Sales Order",
			customer = customer_id,
			items = items,
			transaction_date = order_doc.transaction_date,
			delivery_date = order_doc.transaction_date,
			taxes = taxes,
			connector_address_line1 = order_doc.address_line1,
			connector_address_line2 = order_doc.address_line2,
			connector_city = order_doc.city or 'NA',
			connector_state = order_doc.state,
			connector_email = order_doc.email,
			connector_mobile_no = order_doc.mobile_no,
			connector_country = order_doc.country,
			apply_discount_on = "Grand Total",
			additional_discount_percentage = order_doc.additional_discount_percentage,
			discount_amount = order_doc.discount_amount,
			sales_order_payment = get_payment_details(order_doc),
			reference_num = order_doc.reference_no,
			delivery_time = order_doc.delivery_time,
			sales_team = sales,
			notes = order_doc.notes,
			actual_delivery_date = order_doc.delivery_date,
		))
		so_doc.save(ignore_permissions = True)
		if so_doc.name:
			if int(submit_order):
				so_doc.submit()
			frappe.db.set_value("Connector Sales Order",order_no,"sync",1)
			frappe.db.set_value("Connector Sales Order", order_no, 'status', 'Synced')
			return True
		else:
			return False

def create_sales_invoice(order_no):
	order_doc = frappe.get_doc("Connector Sales Order",order_no)
	if order_doc:
		customer_id = check_customer(order_doc)
		items = get_items(order_doc)
		taxes = get_taxes(order_doc)
		sales = get_sales_team(order_doc)
		delivery_day = str(frappe.db.get_value("Connector Setting","Connector Setting","delivery_day"))
		submit_invoice = frappe.db.get_value("Connector Setting","Connector Setting","submit_invoice")
		si_doc = frappe.get_doc(dict(
			doctype = "Sales Invoice",
			customer = customer_id,
			items = items,
			update_stock = 1,
			is_pos = 1,
			connector_address_line1 = order_doc.address_line1,
			connector_address_line2 = order_doc.address_line2,
			connector_city = order_doc.city or 'NA',
			connector_state = order_doc.state,
			connector_email = order_doc.email,
			connector_mobile_no = order_doc.mobile_no,
			connector_country = order_doc.country,
			pos_profile = order_doc.pos_profile,
			due_date = order_doc.transaction_date,
			posting_date = order_doc.transaction_date,
			reference_number = order_doc.reference_no,
			taxes = taxes,
			sales_team = sales,
			apply_discount_on = "Grand Total",
			additional_discount_percentage = order_doc.additional_discount_percentage,
			discount_amount = order_doc.discount_amount,
			payments = get_payment_details(order_doc)
		))
		si_doc.save(ignore_permissions = True)
		if si_doc.name:
			if int(submit_invoice):
				si_doc.submit()
			frappe.db.set_value("Connector Sales Order",order_no,"sync",1)
			frappe.db.set_value("Connector Sales Order", order_no, 'status', 'Synced')
			return True
	return False


def get_items(order_doc):
	items = []
	for row in order_doc.items:
		item = dict(
			item_code = row.item_code,
			qty = row.qty,
			rate = row.rate,
		uom = row.uom
		)
		items.append(item)
	return items

def get_taxes(order_doc):
	taxes = []
	if order_doc.delivery_charges:
		tax = dict(
			charge_type = "Actual",
			account_head = frappe.db.get_value("Connector Setting","Connector Setting","delivery_account"),
			tax_amount = order_doc.delivery_charges,
			description = "Delivery Charges"
		)
		taxes.append(tax)
	if order_doc.total_taxes_and_charges:
		tax = dict(
			charge_type = "Actual",
			account_head = frappe.db.get_value("Connector Setting","Connector Setting","tax_account"),
			tax_amount = order_doc.total_taxes_and_charges,
			description = "Taxes"
		)
		taxes.append(tax)
	return taxes

def get_sales_person(sales):
	name = None
	if frappe.db.get_value('Sales Person', {'sales_person_name':sales.sales_person }):
		name = frappe.db.get_value('Sales Person', {'sales_person_name':sales.sales_person })
	else:
		doc = frappe.get_doc({
			'doctype': 'Sales Person',
			'sales_person_name':sales.sales_person,
		})
		doc.save()
		name = doc.name
	return name

def get_sales_team(self):
	sales_team = []
	for i in self.sales_team:
		sales_team.append(dict(
			sales_person = get_sales_person(i),
			contact_no = i.contact_no,
			allocated_percentage = i.allocated_percentage or 100,
			allocated_amount = i.allocated_amount,
			commission_rate = i.commission_rate,
			incentives = i.incentives
		))
	return sales_team

def get_payment_details(order_doc):
	payments = []
	bal_amount = 0
	for row in order_doc.connector_payment:
		if row.get('amount') < 0:
			bal_amount += row.get('amount')
			continue
		pay = dict(
			mode_of_payment = row.get('mode_of_payment'), #frappe.db.sql('''select mode_of_payment from `tabPOS Payment Method` where parent=%s and mapper_key=%s''',( order_doc.pos_profile, row.get('mode_of_payment')), as_dict=1)[0].mode_of_payment,
			amount = row.get('amount')
		)
		payments.append(pay)
	payments[0]['amount'] += bal_amount
	return payments


def check_customer(order_doc):
	customer = ''
	address = ''
	if order_doc.customer == 'Walking':
		customer_data= frappe.db.sql("""select name from `tabCustomer` where customer_name=%s""",(order_doc.customer),as_dict=1)
	else:
		if order_doc.mobile_no or order_doc.email:
			customer_data = frappe.db.sql("""select name from `tabCustomer` where email_id=%s and mobile_no=%s""",(order_doc.email,order_doc.mobile_no),as_dict=1)
	if len(customer_data) >= 1:
		customer = customer_data[0].name
	if not customer:
		customer = create_customer(order_doc)
	return customer

def check_address(order_doc,customer):
	address_data = frappe.db.sql("""select p.name as 'name' from `tabDynamic Link` as c inner join `tabAddress` as p on c.parent=p.name where c.link_doctype='Customer' and c.link_name=%s""",customer,as_dict=1)
	if len(address_data) >= 1:
		# frappe.errprint(address_data)
		address_doc = frappe.get_doc("Address",address_data[0].name)
		address_doc.address_line1 = order_doc.address_line1
		address_doc.address_line2 = order_doc.address_line2
		address_doc.city = order_doc.city or 'NA'
		address_doc.state = order_doc.state
		address_doc.country = order_doc.country
		address_doc.email_id = order_doc.email
		address_doc.phone = order_doc.mobile_no
		address_doc.save(ignore_permissions = True)
		return address_data[0].link_name
	else:
		return False


def create_address(order_doc,customer):
	if order_doc.address_line1:
		doc = frappe.get_doc(dict(
			doctype = "Address",
			address_line1 = order_doc.address_line1,
			address_line2 = order_doc.address_line2,
			city = order_doc.city or 'NA',
			state = order_doc.state,
			country = order_doc.country,
			email_id = order_doc.email,
			phone = order_doc.mobile_no
		))
		doc.append("links",{
			"link_doctype":"Customer",
			"link_name":customer
		})
		res = doc.insert(ignore_permissions=True)
		return res.name

def create_customer(order_doc):
	doc = frappe.get_doc(dict(
		doctype = "Customer",
		customer_name = order_doc.customer,
		email_id = order_doc.email,
		mobile_no = order_doc.mobile_no,
		customer_group = frappe.db.get_value("Connector Setting","Connector Setting","customer_group"),
		territory = frappe.db.get_value("Connector Setting","Connector Setting","territory")
	)).insert(ignore_permissions = True)
	return doc.name

def on_submit(self,method):
	for row in self.items:
		row.warehouse_bin = get_bin(row.item_code)


def get_bin(item_code):
	bin = frappe.db.sql("""select c.warehouse_bin as 'warehouse_bin' from `tabItem Warehouse Bin Item` as c inner join `tabItem Warehouse Bin` as p on c.parent=p.name where p.item_code=%s""",(item_code),as_dict=1)
	if bin:
		return bin[0].warehouse_bin

