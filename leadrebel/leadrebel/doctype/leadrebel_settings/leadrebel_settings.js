// Copyright (c) 2024, PC-Giga and contributors
// For license information, please see license.txt

frappe.ui.form.on("LeadRebel Settings", {
	refresh(frm) {
        frm.add_custom_button(__('Manual import'), () => {
            frm.call('import_sessions');
        });
        frm.add_custom_button(__('Match existing leads'), () => {
            frm.call('match_existing_leads');
        });
	}
});
