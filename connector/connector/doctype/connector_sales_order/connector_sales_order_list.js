frappe.listview_settings['Connector Sales Order'] = {
	onload: function(listview) {
		var method = "connector.api.sync_sales_order_multiple";

		listview.page.add_menu_item(__("Sync Order"), function() {
			listview.call_for_selected_items(method,{});
			list_view.refresh();
		});
	}
};