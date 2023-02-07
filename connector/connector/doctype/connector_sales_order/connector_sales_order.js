// Copyright (c) 2020, Bhavesh Maheshwari and contributors
// For license information, please see license.txt

frappe.ui.form.on('Connector Sales Order', {
	refresh:function(frm){
		frm.add_custom_button(__("Create Sales Order"), function(){
			if(frm.doc.sync == 1){
				frappe.msgprint('Order Already Created')
				return
			}
			frappe.call({
				'method': 'connector.api.sync_sales_order',
				'args':{
				'order_no': frm.doc.name
				},
				'callback':function(res){
					if(res.message){
						frappe.msgprint("Sales order created")
					}
				}
			})
		})
	}
});
