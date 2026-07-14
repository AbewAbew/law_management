app_name = "law_management"
app_title = "Law Management"
app_publisher = "Tbest"
app_description = "Legal Practice System"
app_email = "abenezerbehailu20@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext", "hrms", "print_designer"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "law_management",
# 		"logo": "/assets/law_management/logo.png",
# 		"title": "Law Management",
# 		"route": "/law_management",
# 		"has_permission": "law_management.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/law_management/css/law_management.css"
# app_include_js = "/assets/law_management/js/law_management.js"

# include js, css files in header of web template
# web_include_css = "/assets/law_management/css/law_management.css"
# web_include_js = "/assets/law_management/js/law_management.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "law_management/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Leave Application" : "public/js/leave_application_custom.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "law_management/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "law_management.utils.jinja_methods",
# 	"filters": "law_management.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "law_management.install.before_install"
# after_install = "law_management.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "law_management.uninstall.before_uninstall"
# after_uninstall = "law_management.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "law_management.utils.before_app_install"
# after_app_install = "law_management.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "law_management.utils.before_app_uninstall"
# after_app_uninstall = "law_management.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "law_management.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
permission_query_conditions = {
	"Case": "law_management.law_management.doctype.case.case.get_permission_query_conditions",
}
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }
has_permission = {
	"Case": "law_management.law_management.doctype.case.case.has_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Leave Application": {
		"after_insert": "law_management.approval_notifications.notify_leave_application_approvers",
		"on_update": "law_management.approval_notifications.share_leave_application_with_approvers",
	},
	"Expense Claim": {
		"after_insert": "law_management.approval_notifications.notify_expense_claim_approvers",
		"on_update": "law_management.approval_notifications.share_expense_claim_with_approvers",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"law_management.tasks.all"
# 	],
	"daily": [
		"law_management.tasks.check_retainer_expiry",
		"law_management.tasks.check_court_appearances",
		"law_management.tasks.check_retainer_usage",
		"law_management.law_management.doctype.legal_bill.legal_bill.check_automation_rules"
	],
# 	"hourly": [
# 		"law_management.tasks.hourly"
# 	],
# 	"weekly": [
# 		"law_management.tasks.weekly"
# 	],
# 	"monthly": [
# 		"law_management.tasks.monthly"
# 	],
}

# Testing
# -------

# before_tests = "law_management.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "law_management.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "law_management.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["law_management.utils.before_request"]
# after_request = ["law_management.utils.after_request"]

# Job Events
# ----------
# before_job = ["law_management.utils.before_job"]
# after_job = ["law_management.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"law_management.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

law_management_roles = [
	"Legal Associate",
	"Legal Finance",
	"Legal Manager",
	"Legal Paralegal",
	"Legal Partner",
	"IP Manager",
	"IP Staff",
]

law_management_custom_fields = [
	"Customer-senior_mgmt_approval",
	"Customer-custom_kyc__compliance",
	"Customer-custom_referral_details",
	"Customer-custom_referral_source",
	"Customer-custom_referred_by_client",
	"Customer-custom_referred_by_partner",
	"Customer-custom_entity__personal_profile",
	"Customer-custom_legal_form",
	"Customer-custom_date_of_incorporation__birth",
	"Customer-custom_place_of_incorporation__birth",
	"Customer-custom_nationality__jurisdiction",
	"Customer-custom_official_taxreg_number",
	"Customer-custom_employment__business",
	"Customer-custom_occupation__job_title",
	"Customer-custom_name_of_employer",
	"Customer-custom_intended_nature_of_business",
	"Customer-custom_identification_documents",
	"Customer-custom_id_type",
	"Customer-custom_id_number",
	"Customer-custom_issue_date",
	"Customer-custom_expiry_date",
	"Customer-custom_issuing_authority",
	"Customer-custom_risk__financial_profile",
	"Customer-custom_aml_risk_rating",
	"Customer-custom_is_pep",
	"Customer-custom_senior_mgmt_approval_by",
	"Customer-custom_source_of_funds",
	"Customer-custom_source_of_wealth_description",
	"Customer-custom_ownership__structure",
	"Customer-custom_beneficial_owners",
	"Customer-custom_related_entities",
	"Customer-custom_verification_status",
	"Customer-custom_customer_declaration_signed",
	"Customer-custom_address_verified",
	"Customer-custom_kyc_status",
	"Customer-custom_date_of_verification",
	"Leave Application-custom_attachements",
	"Leave Application-custom_medical_certificate",
	"Expense Claim Detail-custom_receipt_attachment",
	"Task-custom_case",
	"Task-assignees",
	"Timesheet Detail-custom_case",
]

law_management_property_setters = [
	"Customer-main-field_order",
	"Customer-naming_series-hidden",
	"Customer-naming_series-reqd",
	"Employee-naming_series-default",
	"Employee-naming_series-options",
	"Leave Application-main-field_order",
	"Leave Application-status-permlevel",
	"Legal Bill-bill_date-in_list_view",
	"Legal Bill-case_reference-in_list_view",
	"Legal Bill-customer-in_list_view",
	"Legal Bill-days_open-in_list_view",
	"Legal Bill-due_date-in_list_view",
	"Legal Bill-ip_case-in_list_view",
	"Legal Bill-status-in_list_view",
	"Task-main-field_order",
	"Task-project-hidden",
	"Timesheet-main-field_order",
	"Timesheet-parent_project-hidden",
	"Timesheet Detail-main-field_order",
]

fixtures = [
	{
		"dt": "Client Script",
		"filters": [["module", "=", "Law Management"]],
	},
	{
		"dt": "Custom Field",
		"filters": [["name", "in", law_management_custom_fields]],
	},
	{
		"dt": "Property Setter",
		"filters": [["name", "in", law_management_property_setters]],
	},
	{
		"dt": "Custom DocPerm",
		"filters": [
			["role", "in", law_management_roles],
			["parent", "!=", "Email Account"],
		],
	},
	{
		"dt": "Role",
		"filters": [["name", "in", law_management_roles]],
	},
	{
		"dt": "Role Profile",
		"filters": [["name", "in", ["Legal"]]],
	},
	{
		"dt": "Print Format",
		"filters": [["name", "in", ["Professional Legal Bill"]]],
	},
	{
		"dt": "Dashboard Chart",
		"filters": [["name", "in", ["Cases by Status", "Legal Invoices"]]],
	},
]
