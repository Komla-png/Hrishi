"""Salary helpers for coach payroll calculations with LOP deductions."""

import calendar
from datetime import date

from utils import CALENDAR_MONTHS


LOP_LEAVE_TYPE_KEYS = {"lop", "lossofpay", "unpaid"}


def _normalize_leave_type_key(leave_type):
	value = (leave_type or "").strip().lower().replace("_", " ")
	return "".join(value.split())


def is_lop_leave_type(leave_type):
	"""Return True when leave type should trigger loss-of-pay deduction."""
	return _normalize_leave_type_key(leave_type) in LOP_LEAVE_TYPE_KEYS


def _month_context(year, month_name):
	month_index = CALENDAR_MONTHS.index(month_name) + 1
	total_days_in_month = calendar.monthrange(year, month_index)[1]
	month_start = date(year, month_index, 1)
	month_end = date(year, month_index, total_days_in_month)
	return month_index, total_days_in_month, month_start.isoformat(), month_end.isoformat()


def count_lop_leave_days_for_month(cur, coach_id, year, month_name):
	"""Count LOP leave days for one coach in one month, including date-range overlaps."""
	_, _, month_start, month_end = _month_context(year, month_name)

	row = cur.execute(
		"""
		SELECT COALESCE(
			SUM(
				CASE
					WHEN date(cl.to_date) < date(?) OR date(cl.from_date) > date(?) THEN 0
					ELSE MAX(
						(julianday(MIN(date(cl.to_date), date(?))) - julianday(MAX(date(cl.from_date), date(?))) + 1)
						- CASE WHEN cl.leave_duration = 'half_day' THEN 0.5 ELSE 0 END,
						0
					)
				END
			),
			0
		) AS lop_leave_days
		FROM coach_leaves cl
		WHERE cl.coach_id = ?
		  AND lower(replace(replace(coalesce(cl.leave_type, ''), ' ', ''), '_', '')) IN ('lop', 'lossofpay', 'unpaid')
		  AND date(cl.to_date) >= date(?)
		  AND date(cl.from_date) <= date(?)
		""",
		(month_start, month_end, month_end, month_start, coach_id, month_start, month_end),
	).fetchone()

	return max(float((row[0] if row else 0) or 0), 0.0)


def get_monthly_salary(cur, coach_id, year, month_name):
	"""Return stored monthly gross salary for one coach and month."""
	row = cur.execute(
		"""
		SELECT COALESCE(salary, 0)
		FROM coach_salaries
		WHERE coach_id = ? AND year = ? AND month = ?
		""",
		(coach_id, year, month_name),
	).fetchone()
	return float((row[0] if row else 0) or 0)


def calculate_final_salary_for_month(cur, coach_id, year, month_name, monthly_salary=None):
	"""Calculate final salary for one coach and month after LOP deduction."""
	_, total_days_in_month, _, _ = _month_context(year, month_name)
	gross_salary = float(monthly_salary if monthly_salary is not None else get_monthly_salary(cur, coach_id, year, month_name))
	per_day_salary = (gross_salary / total_days_in_month) if total_days_in_month > 0 else 0
	lop_leave_days = count_lop_leave_days_for_month(cur, coach_id, year, month_name)
	deduction = lop_leave_days * per_day_salary
	final_salary = max(gross_salary - deduction, 0)

	return {
		"monthly_salary": round(gross_salary, 2),
		"total_days_in_month": total_days_in_month,
		"per_day_salary": round(per_day_salary, 2),
		"lop_leave_days": round(lop_leave_days, 2),
		"deduction": round(deduction, 2),
		"final_salary": round(final_salary, 2),
	}
