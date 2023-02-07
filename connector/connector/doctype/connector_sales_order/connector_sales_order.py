# -*- coding: utf-8 -*-
# Copyright (c) 2020, Bhavesh Maheshwari and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

@frappe.whitelist()
def create_connector_sales_order(args):
	try:
		doc_name = []
		for i in args:
			i['doctype'] = 'Connector Sales Order'
			i['status'] = 'Pending'
			i['sync'] = 0
			doc = frappe.get_doc(i)
			doc.save()
			doc_name.append(doc.name)
		return doc_name
	except Exception as e:
		add_log(str(e))

def get_items(self):
	items = []
	for row in self.items:
		item = dict(
			item_code = row.item_code,
			qty = row.qty,
			rate = row.rate,
		uom = row.uom
		)
		items.append(item)
	return items

def check_customer(self):
	customer = ''
	address = ''
	if self.mobile_no or self.email:
		customer_data = frappe.db.sql("""select name from `tabCustomer` where email_id=%s or mobile_no=%s""",(self.email,self.mobile_no),as_dict=1)
		if len(customer_data) >= 1:
			# frappe.errprint(customer_data)
			customer = customer_data[0].name
	if not customer == "":
		address_res = check_address(self,customer)
		if address_res:
			address = address_res
		else:
			address = create_address(self,customer)
		return customer,address
	else:
		customer = create_customer(self)
		address = create_address(self,customer)
		return customer,address

	

def check_address(self,customer):
	address_data = frappe.db.sql("""select p.name as 'name' from `tabDynamic Link` as c inner join `tabAddress` as p where c.link_doctype='Customer' and c.link_name=%s""",customer,as_dict=1)
	if len(address_data) >= 1:
		# frappe.errprint(address_data)
		address_doc = frappe.get_doc("Address",address_data[0].name)
		address_doc.address_line1 = self.address_line_1
		address_doc.address_line2 = self.address_line_2
		address_doc.city = self.city or 'NA'
		address_doc.state = self.state
		address_doc.country = self.country
		address_doc.email_id = self.email
		address_doc.phone = self.mobile_no
		address_doc.save(ignore_permissions = True)
		return address_data[0].link_name
	else:
		return False


def create_customer(self):
	doc = frappe.get_doc(dict(
		doctype = "Customer",
		customer_name = self.customer,
		email_id = self.email,
		mobile_no = self.mobile_no,
		customer_group = frappe.db.get_value("Connector Setting","Connector Setting","customer_group"),
		territory = frappe.db.get_value("Connector Setting","Connector Setting","territory")
	)).insert(ignore_permissions = True)
	return doc.name

def create_address(self,customer):
	if self.address_line_1:
		doc = frappe.get_doc(dict(
			doctype = "Address",
			address_line1 = self.address_line_1,
			address_line2 = self.address_line_2,
			city = self.city or 'NA',
			state = self.state,
			country = self.country,
			email_id = self.email,
			phone = self.mobile_no
		))
		doc.append("links",{
			"link_doctype":"Customer",
			"link_name":customer
		})
		res = doc.insert(ignore_permissions=True)
		return res.name

def get_taxes(self):
	taxes = []
	if self.delivery_charges:
		tax = dict(
			charge_type = "Actual",
			account_head = frappe.db.get_value("Connector Setting","Connector Setting","delivery_account"),
			tax_amount = self.delivery_charges,
			description = "Delivery Charges"
		)
		taxes.append(tax)
	if self.total_taxes_and_charges:
		tax = dict(
			charge_type = "Actual",
			account_head = frappe.db.get_value("Connector Setting","Connector Setting","tax_account"),
			tax_amount = self.total_taxes_and_charges,
			description = "Taxes"
		)
		taxes.append(tax)
	return taxes

def get_payment_details(self):
	payments = []
	for row in self.connector_payment:
		pay = dict(
			mode_of_payment = row.get('mode_of_payment'),
			amount = row.get('amount')
		)
		payments.append(pay)
	return payments

#add log
def add_log(message):
	file = open('/home/frappe/frappe-bench/apps/connector/connector/connector/doctype/connector_sales_order/connector.log','a')
	file.write(message+'\n')
	file.close()



class ConnectorSalesOrder(Document):
	pass
#	def on_submit(self):
#		customer_id,address_id = check_customer(self)
#		items = get_items(self)
#		taxes = get_taxes(self)
#		delivery_day = str(frappe.db.get_value("Connector Setting","Connector Setting","delivery_day"))
#		submit_order = frappe.db.get_value("Connector Setting","Connector Setting","submit_order")
#		so_doc = frappe.get_doc(dict(
#			doctype = "Sales Order",
#			customer = customer_id,
#			customer_address = address_id,
#			items = items,
#			transaction_date = self.delivery_date,
#			delivery_date = self.delivery_date,
#			taxes = taxes,
#			apply_discount_on = "Grand Total",
#			additional_discount_percentage = self.additional_discount_percentage,
#			discount_amount = self.discount_amount,
#			sales_order_payment = get_payment_details(self),
#			reference_num = self.reference_no,
#		)).insert(ignore_permissions = True)
#		if so_doc:
#			if int(submit_order) == 1:
#				so_doc.submit()
#			frappe.db.set_value("Connector Sales Order",self.name,"sync",1)	
#			frappe.db.set_value("Connector Sales Order",self.name,"status",'Synced')
#			return True
#		else:
#			return False

