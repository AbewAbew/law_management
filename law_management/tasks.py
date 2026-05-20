import frappe
from frappe.utils import add_days, getdate, today

def check_retainer_expiry():
	"""
	Checks for Retainer Schedules that are expiring in 7 days, 1 day, or today.
	"""
	check_days = [7, 1, 0]

	for days in check_days:
		target_date = add_days(today(), days)

		# Find schedules expiring on target_date
		schedules = frappe.db.sql("""
			SELECT
				rs.name as schedule_name,
				rs.end_date,
				rs.parent as case_name,
				c.case_title,
				c.owner,
				c.case_lead
			FROM `tabRetainer Schedule` rs
			JOIN `tabCase` c ON rs.parent = c.name
			WHERE rs.end_date = %s
		""", (target_date,), as_dict=1)

		for schedule in schedules:
			send_expiry_notification(schedule, days)

def send_expiry_notification(schedule, days_remaining):
	# Determine Message
	if days_remaining == 0:
		subject = f"Retainer Period Expiry TODAY: {schedule.case_title}"
		time_msg = "is ending <b>TODAY</b>"
	elif days_remaining == 1:
		subject = f"Retainer Period Expiry Tomorrow: {schedule.case_title}"
		time_msg = "is ending <b>TOMORROW</b>"
	else:
		subject = f"Upcoming Retainer Expiry ({days_remaining} days): {schedule.case_title}"
		time_msg = f"is ending in <b>{days_remaining} days</b>"

	message = f"""
	<h3>Retainer Period Expiring Soon</h3>
	<p>The retainer period <b>{schedule.schedule_name}</b> for Case <b>{schedule.case_title}</b> ({schedule.case_name}) {time_msg} ({schedule.end_date}).</p>
	<p>Please review the case and take necessary actions.</p>
	<br>
	<p><a href="/app/case/{schedule.case_name}">View Case</a></p>
	"""

	recipients = get_recipients(schedule.case_lead, schedule.owner)

	if recipients:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			reference_doctype="Case",
			reference_name=schedule.case_name
		)

def get_recipients(case_lead, case_owner):
	recipients = set()
	if case_lead:
		recipients.add(case_lead)
	# Also include Case Owner (creator) if different? User request emphasized Case Lead + Legal Finance.
	# Standard practice is often to include Owner too, but strict request: "case lead and user with Legal Finance role".
	# The Case Owner (creator) might not be the lead. I'll include lead.

	# Fetch Legal Finance users
	finance_users = frappe.get_all("Has Role", filters={"role": "Legal Finance", "parenttype": "User"}, fields=["parent"])
	for user in finance_users:
		recipients.add(user.parent)

	return list(recipients)

def check_retainer_usage():
	"""
	Checks for active Retainer Schedules where usage exceeds 75% or 90%.
	"""
	# Get schedules that have used hours and allocated hours > 0
	# Focusing on Active cases would be better, but joining is easy enough.
	# We also check flags.

	schedules = frappe.db.sql("""
		SELECT
			rs.name as schedule_name,
			rs.allocated_hours,
			rs.used_hours,
			rs.notification_75_sent,
			rs.notification_90_sent,
			rs.parent as case_name,
			c.case_title,
			c.case_lead,
			c.owner
		FROM `tabRetainer Schedule` rs
		JOIN `tabCase` c ON rs.parent = c.name
		WHERE rs.allocated_hours > 0
		AND rs.used_hours > 0
		AND c.status = 'Active'
		AND (rs.notification_75_sent = 0 OR rs.notification_90_sent = 0)
	""", as_dict=1)

	for schedule in schedules:
		usage_percent = (schedule.used_hours / schedule.allocated_hours) * 100

		# Check 90%
		if usage_percent >= 90 and not schedule.notification_90_sent:
			send_usage_notification(schedule, 90)
			frappe.db.set_value("Retainer Schedule", schedule.schedule_name, "notification_90_sent", 1)

			# If we hit 90 directly without hitting 75 (e.g. big jump), we should probably mark 75 as sent too to avoid late noise
			if not schedule.notification_75_sent:
				frappe.db.set_value("Retainer Schedule", schedule.schedule_name, "notification_75_sent", 1)

		# Check 75%
		elif usage_percent >= 75 and not schedule.notification_75_sent:
			send_usage_notification(schedule, 75)
			frappe.db.set_value("Retainer Schedule", schedule.schedule_name, "notification_75_sent", 1)

def send_usage_notification(schedule, threshold):
	subject = f"Retainer Usage Alert ({threshold}%): {schedule.case_title}"

	current_usage = round((schedule.used_hours / schedule.allocated_hours) * 100, 2)

	message = f"""
	<h3>Retainer Usage High</h3>
	<p>The retainer period <b>{schedule.schedule_name}</b> for Case <b>{schedule.case_title}</b> ({schedule.case_name}) has reached <b>{current_usage}%</b> utilization.</p>
	<ul>
		<li>Allocated: {schedule.allocated_hours} hrs</li>
		<li>Used: {schedule.used_hours} hrs</li>
	</ul>
	<p>Please update the client or review the schedule.</p>
	<br>
	<p><a href="/app/case/{schedule.case_name}">View Case</a></p>
	"""

	recipients = get_recipients(schedule.case_lead, schedule.owner)

	if recipients:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			reference_doctype="Case",
			reference_name=schedule.case_name
		)

def check_court_appearances():
	"""
	Checks for Court Appearances that are in 7 days, 1 day, or today, and sends notifications.
	"""
	# Check for 7 days, 1 day, and 0 days (today)
	# We want specific targets
	check_days = [7, 1, 0]

	for days in check_days:
		target_date = add_days(today(), days)

		# Find cases with appearances on target_date
		# Case must be Active? Assuming we should check all relevant cases.
		# Condition: court_appearance_needed = 1

		# We need to fetch the child table rows directly
		events = frappe.db.sql("""
			SELECT
				ca.name as appearance_name,
				ca.court,
				ca.court_number,
				ca.next_appointment_date,
				ca.legal_staff,
				ca.parent as case_name,
				c.case_title
			FROM `tabCourt Appearance` ca
			JOIN `tabCase` c ON ca.parent = c.name
			WHERE
				DATE(ca.next_appointment_date) = %s
				AND c.court_appearance_needed = 1
		""", (target_date,), as_dict=1)

		for event in events:
			send_court_appearance_notification(event, days)

def send_court_appearance_notification(event, days_remaining):
	# Determine recipients
	recipients = []

	# 1. Legal Staff assigned to this specific appearance
	if event.legal_staff:
		recipients.append(event.legal_staff)

	# 2. All Case Team Members
	team_members = frappe.get_all("Case Member", filters={"parent": event.case_name}, fields=["user"])
	for member in team_members:
		if member.user and member.user not in recipients:
			recipients.append(member.user)

	if not recipients:
		return

	# Message Construction
	if days_remaining == 0:
		subject = f"Court Appearance TODAY: {event.case_title}"
		time_msg = "is scheduled for <b>TODAY</b>"
	elif days_remaining == 1:
		subject = f"Court Appearance Tomorrow: {event.case_title}"
		time_msg = "is scheduled for <b>TOMORROW</b>"
	else:
		subject = f"Upcoming Court Appearance ({days_remaining} days): {event.case_title}"
		time_msg = f"is coming up in <b>{days_remaining} days</b>"

	message = f"""
	<h3>Court Appearance Reminder</h3>
	<p>A court appearance for Case <b>{event.case_title}</b> ({event.case_name}) {time_msg}.</p>
	<ul>
		<li><b>Date:</b> {event.next_appointment_date}</li>
		<li><b>Court:</b> {event.court}</li>
		<li><b>Court No:</b> {event.court_number or 'N/A'}</li>
	</ul>
	<p>Please ensure you are prepared.</p>
	<br>
	<p><a href="/app/case/{event.case_name}">View Case</a></p>
	"""

	frappe.sendmail(
		recipients=recipients,
		subject=subject,
		message=message,
		reference_doctype="Case",
		reference_name=event.case_name
	)
