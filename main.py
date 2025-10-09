# import os
# import re
# import urllib.parse
# from typing import List, Optional, Dict, Any
# from difflib import SequenceMatcher
# from datetime import datetime, date

# # third-party
# import mysql.connector
# from fastmcp import FastMCP

# # optional Levenshtein import
# try:
#     import Levenshtein
# except ImportError:
#     Levenshtein = None  # we'll check later

# # For health route responses (used by FastMCP custom_route)
# from starlette.requests import Request
# from starlette.responses import PlainTextResponse, JSONResponse

# # -------------------------------
# # MCP server
# # -------------------------------
# mcp = FastMCP("LeaveManager")

# # -------------------------------
# # MySQL connection (reads from env)
# # -------------------------------
# def get_connection():
#     """
#     Read DB credentials from environment variables
#     """
#     return mysql.connector.connect(
#         host=os.environ.get("DB_HOST", "103.174.10.72"),
#         user=os.environ.get("DB_USER", "tt_crm_mcp"),
#         password=os.environ.get("DB_PASSWORD", "F*PAtqhu@sg2w58n"),
#         database=os.environ.get("DB_NAME", "tt_crm_mcp"),
#         port=int(os.environ.get("DB_PORT", "3306")),
#     )

# # -------------------------------
# # AI-Powered Name Matching Utilities
# # -------------------------------
# class NameMatcher:
#     @staticmethod
#     def normalize_name(name: str) -> str:
#         name = name.lower().strip()
#         name = re.sub(r'[^\w\s]', '', name)
#         name = re.sub(r'\s+', ' ', name)
#         return name

#     @staticmethod
#     def similarity_score(name1: str, name2: str) -> float:
#         name1_norm = NameMatcher.normalize_name(name1)
#         name2_norm = NameMatcher.normalize_name(name2)

#         # If Levenshtein is available, use it; otherwise fall back to simple ratio
#         if Levenshtein:
#             levenshtein_sim = 1 - (Levenshtein.distance(name1_norm, name2_norm) / max(len(name1_norm), len(name2_norm), 1))
#         else:
#             # naive fallback: approximate by SequenceMatcher
#             levenshtein_sim = SequenceMatcher(None, name1_norm, name2_norm).ratio()

#         sequence_sim = SequenceMatcher(None, name1_norm, name2_norm).ratio()
#         combined_score = (levenshtein_sim * 0.6) + (sequence_sim * 0.4)
#         return combined_score

#     @staticmethod
#     def extract_name_parts(full_name: str) -> Dict[str, str]:
#         parts = full_name.split()
#         if len(parts) == 1:
#             return {'first': parts[0], 'last': ''}
#         elif len(parts) == 2:
#             return {'first': parts[0], 'last': parts[1]}
#         else:
#             return {'first': parts[0], 'last': parts[-1]}

#     @staticmethod
#     def fuzzy_match_employee(search_name: str, employees: List[Dict[str, Any]], threshold: float = 0.6) -> List[Dict[str, Any]]:
#         matches = []
#         search_parts = NameMatcher.extract_name_parts(search_name)

#         for emp in employees:
#             scores = []
#             emp_full_name = f"{emp.get('developer_name','')}".strip()
#             scores.append(NameMatcher.similarity_score(search_name, emp_full_name))
            
#             # Try first + last name combination
#             if ' ' in emp_full_name:
#                 first_name = emp_full_name.split()[0]
#                 last_name = ' '.join(emp_full_name.split()[1:])
#                 scores.append(NameMatcher.similarity_score(search_name, f"{first_name} {last_name}"))
#                 scores.append(NameMatcher.similarity_score(search_name, f"{last_name} {first_name}"))

#             if search_parts['last']:
#                 first_score = NameMatcher.similarity_score(search_parts['first'], emp_full_name.split()[0] if emp_full_name else '')
#                 last_score = NameMatcher.similarity_score(search_parts['last'], ' '.join(emp_full_name.split()[1:]) if ' ' in emp_full_name else '')
#                 if first_score > 0 or last_score > 0:
#                     scores.append((first_score + last_score) / 2)

#             best_score = max(scores) if scores else 0
#             if best_score >= threshold:
#                 matches.append({'employee': emp, 'score': best_score, 'match_type': 'fuzzy'})

#         matches.sort(key=lambda x: x['score'], reverse=True)
#         return matches

# # -------------------------------
# # Enhanced Employee Search with AI
# # -------------------------------
# def fetch_employees_ai(search_term: str = None, emp_id: int = None) -> List[Dict[str, Any]]:
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         if emp_id:
#             cursor.execute("""
#                 SELECT d.id, d.developer_name, d.designation, d.email_id, d.mobile, 
#                        d.status, d.doj, d.emp_number, d.blood_group,
#                        u.username
#                 FROM developer d
#                 LEFT JOIN user u ON d.user_id = u.user_id
#                 WHERE d.id = %s
#             """, (emp_id,))
#         elif search_term:
#             cursor.execute("""
#                 SELECT d.id, d.developer_name, d.designation, d.email_id, d.mobile, 
#                        d.status, d.doj, d.emp_number, d.blood_group,
#                        u.username
#                 FROM developer d
#                 LEFT JOIN user u ON d.user_id = u.user_id
#                 WHERE d.developer_name LIKE %s OR d.email_id LIKE %s 
#                    OR d.mobile LIKE %s OR d.emp_number LIKE %s
#                 ORDER BY d.developer_name
#             """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
#         else:
#             return []

#         rows = cursor.fetchall()

#         if search_term and not rows:
#             cursor.execute("""
#                 SELECT d.id, d.developer_name, d.designation, d.email_id, d.mobile, 
#                        d.status, d.doj, d.emp_number, d.blood_group,
#                        u.username
#                 FROM developer d
#                 LEFT JOIN user u ON d.user_id = u.user_id
#                 WHERE d.status = 1
#             """)
#             all_employees = cursor.fetchall()
#             fuzzy_matches = NameMatcher.fuzzy_match_employee(search_term, all_employees)
#             rows = [match['employee'] for match in fuzzy_matches[:5]]

#         return rows

#     except Exception as e:
#         print(f"Database error: {e}")
#         return []
#     finally:
#         cursor.close()
#         conn.close()

# # -------------------------------
# # Leave Management Functions
# # -------------------------------
# def get_leave_balance_for_employee(developer_id: int) -> Dict[str, Any]:
#     """Calculate leave balance for an employee"""
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         # Get opening leave balance from developer table
#         cursor.execute("""
#             SELECT opening_leave_balance, doj, status 
#             FROM developer 
#             WHERE id = %s
#         """, (developer_id,))
#         developer_info = cursor.fetchone()
        
#         if not developer_info:
#             return {"error": "Employee not found"}
        
#         # Calculate used leaves from leave_requests table
#         cursor.execute("""
#             SELECT leave_type, COUNT(*) as count
#             FROM leave_requests 
#             WHERE developer_id = %s AND status = 'Approved'
#             GROUP BY leave_type
#         """, (developer_id,))
        
#         leave_counts = cursor.fetchall()
        
#         # Calculate used leaves (convert different leave types to day equivalents)
#         used_leaves = 0
#         for leave in leave_counts:
#             if leave['leave_type'] == 'FULL DAY':
#                 used_leaves += leave['count']
#             elif leave['leave_type'] in ['HALF DAY', 'Compensation Half Day']:
#                 used_leaves += leave['count'] * 0.5
#             elif leave['leave_type'] in ['2 hrs', 'Compensation 2 hrs']:
#                 used_leaves += leave['count'] * 0.25
        
#         opening_balance = developer_info['opening_leave_balance'] or 0
#         current_balance = opening_balance - used_leaves
        
#         return {
#             "opening_balance": opening_balance,
#             "used_leaves": used_leaves,
#             "current_balance": current_balance,
#             "leave_details": leave_counts
#         }
        
#     except Exception as e:
#         return {"error": f"Error calculating leave balance: {str(e)}"}
#     finally:
#         cursor.close()
#         conn.close()

# def get_employee_work_report(developer_id: int, days: int = 30) -> List[Dict[str, Any]]:
#     """Get recent work reports for an employee"""
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         cursor.execute("""
#             SELECT wr.task, wr.description, wr.date, wr.total_time, 
#                    p.title as project_name, c.client_name
#             FROM work_report wr
#             LEFT JOIN project p ON wr.project_id = p.id
#             LEFT JOIN client c ON wr.client_id = c.id
#             WHERE wr.developer_id = %s 
#             AND wr.date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
#             ORDER BY wr.date DESC
#             LIMIT 20
#         """, (developer_id, days))
        
#         return cursor.fetchall()
        
#     except Exception as e:
#         print(f"Error fetching work report: {e}")
#         return []
#     finally:
#         cursor.close()
#         conn.close()

# def get_employee_leave_requests(developer_id: int) -> List[Dict[str, Any]]:
#     """Get leave requests for an employee"""
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         cursor.execute("""
#             SELECT request_id, leave_type, date_of_leave, status, 
#                    dev_comments, admin_comments, created_at
#             FROM leave_requests 
#             WHERE developer_id = %s 
#             ORDER BY date_of_leave DESC
#             LIMIT 10
#         """, (developer_id,))
        
#         return cursor.fetchall()
        
#     except Exception as e:
#         print(f"Error fetching leave requests: {e}")
#         return []
#     finally:
#         cursor.close()
#         conn.close()

# # -------------------------------
# # Employee Formatting and Resolution
# # -------------------------------
# def format_employee_options(employees: List[Dict[str, Any]]) -> str:
#     options = []
#     for i, emp in enumerate(employees, 1):
#         option = f"{i}. 👤 {emp.get('developer_name','Unknown')}"
#         if emp.get('designation'):
#             option += f" | 💼 {emp.get('designation')}"
#         if emp.get('email_id'):
#             option += f" | 📧 {emp.get('email_id')}"
#         if emp.get('emp_number'):
#             option += f" | 🆔 {emp.get('emp_number')}"
#         if emp.get('mobile'):
#             option += f" | 📞 {emp.get('mobile')}"
#         status = "Active" if emp.get('status') == 1 else "Inactive"
#         option += f" | 🔰 {status}"
#         options.append(option)
#     return "\n".join(options)

# def resolve_employee_ai(search_name: str, additional_context: str = None) -> Dict[str, Any]:
#     employees = fetch_employees_ai(search_term=search_name)

#     if not employees:
#         return {'status': 'not_found', 'message': f"No employees found matching '{search_name}'"}

#     if len(employees) == 1:
#         return {'status': 'resolved', 'employee': employees[0]}

#     if additional_context:
#         context_lower = additional_context.lower()
#         filtered_employees = []
#         for emp in employees:
#             designation = (emp.get('designation') or '').lower()
#             email = (emp.get('email_id') or '').lower()
#             emp_number = (emp.get('emp_number') or '').lower()
            
#             if (context_lower in designation or 
#                 context_lower in email or 
#                 context_lower in emp_number or
#                 context_lower in emp.get('developer_name', '').lower()):
#                 filtered_employees.append(emp)
        
#         if len(filtered_employees) == 1:
#             return {'status': 'resolved', 'employee': filtered_employees[0]}

#     return {
#         'status': 'ambiguous',
#         'employees': employees,
#         'message': f"Found {len(employees)} employees. Please specify:"
#     }

# # -------------------------------
# # MCP Tools
# # -------------------------------
# @mcp.tool()
# def get_employee_details(name: str, additional_context: Optional[str] = None) -> str:
#     """Get comprehensive details for an employee including personal info, leave balance, and recent activity"""
#     resolution = resolve_employee_ai(name, additional_context)
    
#     if resolution['status'] == 'not_found':
#         return f"❌ No employee found matching '{name}'."
    
#     if resolution['status'] == 'ambiguous':
#         options_text = format_employee_options(resolution['employees'])
#         return f"🔍 {resolution['message']}\n\n{options_text}\n\n💡 Tip: You can specify by:\n- Designation (e.g., 'Developer')\n- Email\n- Employee number\n- Or say the number (e.g., '1')"

#     emp = resolution['employee']
    
#     # Get additional information
#     leave_balance = get_leave_balance_for_employee(emp['id'])
#     work_reports = get_employee_work_report(emp['id'], days=7)
#     leave_requests = get_employee_leave_requests(emp['id'])
    
#     response = f"✅ **Employee Details**\n\n"
#     response += f"👤 **{emp['developer_name']}**\n"
#     response += f"🆔 Employee ID: {emp['id']} | Employee #: {emp.get('emp_number', 'N/A')}\n"
#     response += f"💼 Designation: {emp.get('designation', 'N/A')}\n"
#     response += f"📧 Email: {emp.get('email_id', 'N/A')}\n"
#     response += f"📞 Mobile: {emp.get('mobile', 'N/A')}\n"
#     response += f"🩸 Blood Group: {emp.get('blood_group', 'N/A')}\n"
#     response += f"📅 Date of Joining: {emp.get('doj', 'N/A')}\n"
#     response += f"🔰 Status: {'Active' if emp.get('status') == 1 else 'Inactive'}\n\n"
    
#     # Leave Balance
#     if 'error' not in leave_balance:
#         response += f"📊 **Leave Balance:** {leave_balance['current_balance']:.1f} days\n"
#         response += f"   - Opening Balance: {leave_balance['opening_balance']}\n"
#         response += f"   - Leaves Used: {leave_balance['used_leaves']:.1f} days\n\n"
#     else:
#         response += f"📊 Leave Balance: Data not available\n\n"
    
#     # Recent Work Reports
#     if work_reports:
#         response += f"📋 **Recent Work (Last 7 days):**\n"
#         for report in work_reports[:3]:  # Show last 3 reports
#             hours = report['total_time'] / 3600 if report['total_time'] else 0
#             response += f"   - {report['date']}: {report['task'][:50]}... ({hours:.1f}h)\n"
#         response += "\n"
    
#     # Recent Leave Requests
#     if leave_requests:
#         response += f"🏖️  **Recent Leave Requests:**\n"
#         for leave in leave_requests[:3]:  # Show last 3 leaves
#             status_icon = "✅" if leave['status'] == 'Approved' else "⏳" if leave['status'] == 'Pending' else "❌"
#             response += f"   - {leave['date_of_leave']}: {leave['leave_type']} {status_icon}\n"
    
#     return response

# @mcp.tool()
# def get_leave_balance(name: str, additional_context: Optional[str] = None) -> str:
#     """Get detailed leave balance information for an employee"""
#     resolution = resolve_employee_ai(name, additional_context)
    
#     if resolution['status'] == 'not_found':
#         return f"❌ No employee found matching '{name}'."
    
#     if resolution['status'] == 'ambiguous':
#         options_text = format_employee_options(resolution['employees'])
#         return f"🔍 {resolution['message']}\n\n{options_text}"

#     emp = resolution['employee']
#     leave_balance = get_leave_balance_for_employee(emp['id'])
    
#     if 'error' in leave_balance:
#         return f"❌ Error retrieving leave balance for {emp['developer_name']}: {leave_balance['error']}"
    
#     response = f"📊 **Leave Balance for {emp['developer_name']}**\n\n"
#     response += f"💼 Designation: {emp.get('designation', 'N/A')}\n"
#     response += f"📧 Email: {emp.get('email_id', 'N/A')}\n\n"
    
#     response += f"💰 **Current Balance:** {leave_balance['current_balance']:.1f} days\n"
#     response += f"📥 Opening Balance: {leave_balance['opening_balance']} days\n"
#     response += f"📤 Leaves Used: {leave_balance['used_leaves']:.1f} days\n\n"
    
#     if leave_balance['leave_details']:
#         response += f"📋 **Breakdown of Used Leaves:**\n"
#         for leave in leave_balance['leave_details']:
#             days = 1 if leave['leave_type'] == 'FULL DAY' else 0.5 if leave['leave_type'] in ['HALF DAY', 'Compensation Half Day'] else 0.25
#             total_days = leave['count'] * days
#             response += f"   - {leave['leave_type']}: {leave['count']} times ({total_days:.1f} days)\n"
    
#     return response

# @mcp.tool()
# def get_work_report(name: str, days: int = 7, additional_context: Optional[str] = None) -> str:
#     """Get work report for an employee for specified number of days"""
#     resolution = resolve_employee_ai(name, additional_context)
    
#     if resolution['status'] == 'not_found':
#         return f"❌ No employee found matching '{name}'."
    
#     if resolution['status'] == 'ambiguous':
#         options_text = format_employee_options(resolution['employees'])
#         return f"🔍 {resolution['message']}\n\n{options_text}"

#     emp = resolution['employee']
#     work_reports = get_employee_work_report(emp['id'], days)
    
#     response = f"📋 **Work Report for {emp['developer_name']}**\n"
#     response += f"💼 Designation: {emp.get('designation', 'N/A')}\n"
#     response += f"📅 Period: Last {days} days\n\n"
    
#     if not work_reports:
#         response += "No work reports found for the specified period."
#         return response
    
#     total_hours = 0
#     for report in work_reports:
#         hours = report['total_time'] / 3600 if report['total_time'] else 0
#         total_hours += hours
        
#         response += f"**{report['date']}** - {report.get('project_name', 'No Project')}\n"
#         response += f"Client: {report.get('client_name', 'N/A')}\n"
#         response += f"Task: {report['task'][:100]}{'...' if len(report['task']) > 100 else ''}\n"
#         if report['description']:
#             response += f"Details: {report['description'][:100]}{'...' if len(report['description']) > 100 else ''}\n"
#         response += f"Hours: {hours:.1f}h\n"
#         response += "---\n"
    
#     response += f"\n**Total Hours ({days} days): {total_hours:.1f}h**\n"
#     response += f"Average per day: {total_hours/days:.1f}h" if days > 0 else ""
    
#     return response

# @mcp.tool()
# def get_leave_history(name: str, additional_context: Optional[str] = None) -> str:
#     """Get leave history for an employee"""
#     resolution = resolve_employee_ai(name, additional_context)
    
#     if resolution['status'] == 'not_found':
#         return f"❌ No employee found matching '{name}'."
    
#     if resolution['status'] == 'ambiguous':
#         options_text = format_employee_options(resolution['employees'])
#         return f"🔍 {resolution['message']}\n\n{options_text}"

#     emp = resolution['employee']
#     leave_requests = get_employee_leave_requests(emp['id'])
    
#     response = f"🏖️  **Leave History for {emp['developer_name']}**\n"
#     response += f"💼 Designation: {emp.get('designation', 'N/A')}\n\n"
    
#     if not leave_requests:
#         response += "No leave requests found."
#         return response
    
#     approved_count = sum(1 for lr in leave_requests if lr['status'] == 'Approved')
#     pending_count = sum(1 for lr in leave_requests if lr['status'] in ['Requested', 'Pending'])
#     declined_count = sum(1 for lr in leave_requests if lr['status'] == 'Declined')
    
#     response += f"📊 Summary: {approved_count} Approved, {pending_count} Pending, {declined_count} Declined\n\n"
    
#     for leave in leave_requests:
#         status_icon = "✅" if leave['status'] == 'Approved' else "⏳" if leave['status'] in ['Requested', 'Pending'] else "❌"
#         response += f"**{leave['date_of_leave']}** - {leave['leave_type']} {status_icon}\n"
#         if leave['dev_comments']:
#             response += f"Reason: {leave['dev_comments']}\n"
#         if leave['admin_comments'] and leave['status'] != 'Pending':
#             response += f"Admin Note: {leave['admin_comments']}\n"
#         response += "---\n"
    
#     return response

# @mcp.tool()
# def search_employees(search_query: str) -> str:
#     """Search for employees by name, designation, email, or employee number"""
#     employees = fetch_employees_ai(search_term=search_query)
    
#     if not employees:
#         return f"❌ No employees found matching '{search_query}'"
    
#     response = f"🔍 **Search Results for '{search_query}':**\n\n"
    
#     for i, emp in enumerate(employees, 1):
#         response += f"{i}. **{emp['developer_name']}**\n"
#         response += f"   💼 {emp.get('designation', 'N/A')}\n"
#         response += f"   📧 {emp.get('email_id', 'N/A')}\n"
#         response += f"   📞 {emp.get('mobile', 'N/A')}\n"
#         response += f"   🆔 {emp.get('emp_number', 'N/A')}\n"
#         response += f"   🔰 {'Active' if emp.get('status') == 1 else 'Inactive'}\n"
        
#         # Get quick leave balance
#         leave_balance = get_leave_balance_for_employee(emp['id'])
#         if 'error' not in leave_balance:
#             response += f"   📊 Leave Balance: {leave_balance['current_balance']:.1f} days\n"
        
#         response += "\n"
    
#     return response

# # -------------------------------
# # MCP Endpoint
# # -------------------------------
# @mcp.custom_route("/mcp", methods=["POST"])
# async def mcp_endpoint(request: Request):
#     """MCP protocol endpoint"""
#     return JSONResponse({"status": "MCP server is running"})

# @mcp.custom_route("/health", methods=["GET"])
# async def health_check(request: Request) -> PlainTextResponse:
#     return PlainTextResponse("OK")

# @mcp.custom_route("/", methods=["GET"])
# async def root(request: Request) -> JSONResponse:
#     return JSONResponse({
#         "message": "Leave Manager MCP Server",
#         "status": "running",
#         "version": "1.16.1"
#     })

# # -------------------------------
# # Run MCP server
# # -------------------------------
# if __name__ == "__main__":
#     # Optional: warn if Levenshtein missing
#     if Levenshtein is None:
#         print("Warning: python-levenshtein not installed. Fuzzy quality will be slightly lower. Install with: pip install python-Levenshtein")

#     transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
#     host = os.environ.get("MCP_HOST", "0.0.0.0")
#     port = int(os.environ.get("PORT", "8080"))

#     print(f"Starting Leave Manager MCP Server on {host}:{port} with {transport} transport")
#     mcp.run(transport=transport, host=host, port=port)
#!/usr/bin/env python3
"""
mcp_server_full.py

Extended MCP server for Leave Management + HR Activities + Company Management
based on the tt_crm_mcp database schema.

Usage:
    export DB_HOST=...
    export DB_USER=...
    export DB_PASSWORD=...
    export DB_NAME=...
    python mcp_server_full.py
"""

import os
import re
import urllib.parse
from typing import List, Optional, Dict, Any
from difflib import SequenceMatcher
from datetime import datetime, date, timedelta

# third-party
import mysql.connector
from fastmcp import FastMCP

# optional Levenshtein import
try:
    import Levenshtein
except Exception:
    Levenshtein = None

# For health route responses (used by FastMCP custom_route)
from starlette.requests import Request
from starlette.responses import PlainTextResponse, JSONResponse

# -------------------------------
# MCP server
# -------------------------------
mcp = FastMCP("LeaveManagerPlus")

# -------------------------------
# MySQL connection (reads from env)
# -------------------------------
def get_connection():
    """
    Read DB credentials from environment variables
    """
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "103.174.10.72"),
        user=os.environ.get("DB_USER", "tt_crm_mcp"),
        password=os.environ.get("DB_PASSWORD", "F*PAtqhu@sg2w58n"),
        database=os.environ.get("DB_NAME", "tt_crm_mcp"),
        port=int(os.environ.get("DB_PORT", "3306")),
        autocommit=True,
    )

# -------------------------------
# AI-Powered Name Matching Utilities
# -------------------------------
class NameMatcher:
    @staticmethod
    def normalize_name(name: str) -> str:
        name = (name or "").lower().strip()
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name

    @staticmethod
    def similarity_score(name1: str, name2: str) -> float:
        name1_norm = NameMatcher.normalize_name(name1)
        name2_norm = NameMatcher.normalize_name(name2)

        if Levenshtein:
            try:
                dist = Levenshtein.distance(name1_norm, name2_norm)
                levenshtein_sim = 1 - (dist / max(len(name1_norm), len(name2_norm), 1))
            except Exception:
                levenshtein_sim = SequenceMatcher(None, name1_norm, name2_norm).ratio()
        else:
            levenshtein_sim = SequenceMatcher(None, name1_norm, name2_norm).ratio()

        sequence_sim = SequenceMatcher(None, name1_norm, name2_norm).ratio()
        combined_score = (levenshtein_sim * 0.6) + (sequence_sim * 0.4)
        return combined_score

    @staticmethod
    def extract_name_parts(full_name: str) -> Dict[str, str]:
        parts = (full_name or "").split()
        if len(parts) == 0:
            return {'first': '', 'last': ''}
        if len(parts) == 1:
            return {'first': parts[0], 'last': ''}
        elif len(parts) == 2:
            return {'first': parts[0], 'last': parts[1]}
        else:
            return {'first': parts[0], 'last': parts[-1]}

    @staticmethod
    def fuzzy_match_employee(search_name: str, employees: List[Dict[str, Any]], threshold: float = 0.6) -> List[Dict[str, Any]]:
        matches = []
        search_parts = NameMatcher.extract_name_parts(search_name)

        for emp in employees:
            scores = []
            emp_full_name = f"{emp.get('developer_name','')}".strip()
            scores.append(NameMatcher.similarity_score(search_name, emp_full_name))

            if ' ' in emp_full_name:
                first_name = emp_full_name.split()[0]
                last_name = ' '.join(emp_full_name.split()[1:])
                scores.append(NameMatcher.similarity_score(search_name, f"{first_name} {last_name}"))
                scores.append(NameMatcher.similarity_score(search_name, f"{last_name} {first_name}"))

            if search_parts['last']:
                first_score = NameMatcher.similarity_score(search_parts['first'], emp_full_name.split()[0] if emp_full_name else '')
                last_score = NameMatcher.similarity_score(search_parts['last'], ' '.join(emp_full_name.split()[1:]) if ' ' in emp_full_name else '')
                if first_score > 0 or last_score > 0:
                    scores.append((first_score + last_score) / 2)

            best_score = max(scores) if scores else 0
            if best_score >= threshold:
                matches.append({'employee': emp, 'score': best_score, 'match_type': 'fuzzy'})

        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches

# -------------------------------
# Enhanced Employee Search with AI
# -------------------------------
def fetch_employees_ai(search_term: str = None, emp_id: int = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if emp_id:
            cursor.execute("""
                SELECT d.id, d.developer_name, d.designation, d.email_id, d.mobile, 
                       d.status, d.doj, d.emp_number, d.blood_group,
                       u.username, d.opening_leave_balance, d.is_pf_enabled, d.pf_join_date
                FROM developer d
                LEFT JOIN user u ON d.user_id = u.user_id
                WHERE d.id = %s
            """, (emp_id,))
        elif search_term:
            cursor.execute("""
                SELECT d.id, d.developer_name, d.designation, d.email_id, d.mobile, 
                       d.status, d.doj, d.emp_number, d.blood_group,
                       u.username, d.opening_leave_balance, d.is_pf_enabled, d.pf_join_date
                FROM developer d
                LEFT JOIN user u ON d.user_id = u.user_id
                WHERE d.developer_name LIKE %s OR d.email_id LIKE %s 
                   OR d.mobile LIKE %s OR d.emp_number LIKE %s
                ORDER BY d.developer_name
            """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        else:
            return []

        rows = cursor.fetchall()

        if search_term and not rows:
            # fallback fuzzy search among active employees
            cursor.execute("""
                SELECT d.id, d.developer_name, d.designation, d.email_id, d.mobile, 
                       d.status, d.doj, d.emp_number, d.blood_group,
                       u.username, d.opening_leave_balance, d.is_pf_enabled, d.pf_join_date
                FROM developer d
                LEFT JOIN user u ON d.user_id = u.user_id
                WHERE d.status = 1
            """)
            all_employees = cursor.fetchall()
            fuzzy_matches = NameMatcher.fuzzy_match_employee(search_term, all_employees)
            rows = [match['employee'] for match in fuzzy_matches[:5]]

        return rows

    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# -------------------------------
# Leave Management Functions
# -------------------------------
def get_leave_balance_for_employee(developer_id: int) -> Dict[str, Any]:
    """Calculate leave balance for an employee"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT opening_leave_balance, doj, status 
            FROM developer 
            WHERE id = %s
        """, (developer_id,))
        developer_info = cursor.fetchone()
        
        if not developer_info:
            return {"error": "Employee not found"}
        
        cursor.execute("""
            SELECT leave_type, COUNT(*) as count
            FROM leave_requests 
            WHERE developer_id = %s AND status = 'Approved'
            GROUP BY leave_type
        """, (developer_id,))
        leave_counts = cursor.fetchall()
        
        used_leaves = 0.0
        for leave in leave_counts:
            lt = (leave.get('leave_type') or '').upper()
            cnt = float(leave.get('count') or 0)
            if lt == 'FULL DAY':
                used_leaves += cnt
            elif lt in ['HALF DAY', 'COMPENSATION HALF DAY']:
                used_leaves += cnt * 0.5
            elif lt in ['2 HRS', 'COMPENSATION 2 HRS']:
                used_leaves += cnt * 0.25
            else:
                # default treat as full day for unknown types
                used_leaves += cnt

        opening_balance = float(developer_info.get('opening_leave_balance') or 0)
        current_balance = opening_balance - used_leaves
        
        return {
            "opening_balance": opening_balance,
            "used_leaves": used_leaves,
            "current_balance": current_balance,
            "leave_details": leave_counts
        }
        
    except Exception as e:
        return {"error": f"Error calculating leave balance: {str(e)}"}
    finally:
        cursor.close()
        conn.close()

def get_employee_work_report(developer_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Get recent work reports for an employee"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT wr.task, wr.description, wr.date, wr.total_time, 
                   p.title as project_name, c.client_name
            FROM work_report wr
            LEFT JOIN project p ON wr.project_id = p.id
            LEFT JOIN client c ON wr.client_id = c.id
            WHERE wr.developer_id = %s 
            AND wr.date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY wr.date DESC
            LIMIT 100
        """, (developer_id, days))
        
        return cursor.fetchall()
        
    except Exception as e:
        print(f"Error fetching work report: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_employee_leave_requests(developer_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Get leave requests for an employee"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT request_id, leave_type, date_of_leave, status, 
                   dev_comments, admin_comments, created_at
            FROM leave_requests 
            WHERE developer_id = %s 
            ORDER BY date_of_leave DESC
            LIMIT %s
        """, (developer_id, limit))
        
        return cursor.fetchall()
        
    except Exception as e:
        print(f"Error fetching leave requests: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# -------------------------------
# Employee Formatting and Resolution
# -------------------------------
def format_employee_options(employees: List[Dict[str, Any]]) -> str:
    options = []
    for i, emp in enumerate(employees, 1):
        option = f"{i}. 👤 {emp.get('developer_name','Unknown')}"
        if emp.get('designation'):
            option += f" | 💼 {emp.get('designation')}"
        if emp.get('email_id'):
            option += f" | 📧 {emp.get('email_id')}"
        if emp.get('emp_number'):
            option += f" | 🆔 {emp.get('emp_number')}"
        if emp.get('mobile'):
            option += f" | 📞 {emp.get('mobile')}"
        status = "Active" if emp.get('status') == 1 else "Inactive"
        option += f" | 🔰 {status}"
        options.append(option)
    return "\n".join(options)

def resolve_employee_ai(search_name: str, additional_context: str = None) -> Dict[str, Any]:
    employees = fetch_employees_ai(search_term=search_name)

    if not employees:
        return {'status': 'not_found', 'message': f"No employees found matching '{search_name}'"}

    if len(employees) == 1:
        return {'status': 'resolved', 'employee': employees[0]}

    if additional_context:
        context_lower = (additional_context or '').lower()
        filtered_employees = []
        for emp in employees:
            designation = (emp.get('designation') or '').lower()
            email = (emp.get('email_id') or '').lower()
            emp_number = (emp.get('emp_number') or '').lower()
            
            if (context_lower in designation or 
                context_lower in email or 
                context_lower in emp_number or
                context_lower in emp.get('developer_name', '').lower()):
                filtered_employees.append(emp)
        
        if len(filtered_employees) == 1:
            return {'status': 'resolved', 'employee': filtered_employees[0]}

    return {
        'status': 'ambiguous',
        'employees': employees,
        'message': f"Found {len(employees)} employees. Please specify:"
    }

# -------------------------------
# Existing tools (kept) + new HR tools
# -------------------------------
@mcp.tool()
def get_employee_details(name: str, additional_context: Optional[str] = None) -> str:
    """Get comprehensive details for an employee including personal info, leave balance, and recent activity"""
    resolution = resolve_employee_ai(name, additional_context)
    
    if resolution['status'] == 'not_found':
        return f"❌ No employee found matching '{name}'."
    
    if resolution['status'] == 'ambiguous':
        options_text = format_employee_options(resolution['employees'])
        return f"🔍 {resolution['message']}\n\n{options_text}\n\n💡 Tip: You can specify by:\n- Designation (e.g., 'Developer')\n- Email\n- Employee number\n- Or say the number (e.g., '1')"

    emp = resolution['employee']
    
    # Get additional information
    leave_balance = get_leave_balance_for_employee(emp['id'])
    work_reports = get_employee_work_report(emp['id'], days=7)
    leave_requests = get_employee_leave_requests(emp['id'], limit=10)
    
    response = f"✅ **Employee Details**\n\n"
    response += f"👤 **{emp['developer_name']}**\n"
    response += f"🆔 Employee ID: {emp['id']} | Employee #: {emp.get('emp_number', 'N/A')}\n"
    response += f"💼 Designation: {emp.get('designation', 'N/A')}\n"
    response += f"📧 Email: {emp.get('email_id', 'N/A')}\n"
    response += f"📞 Mobile: {emp.get('mobile', 'N/A')}\n"
    response += f"🩸 Blood Group: {emp.get('blood_group', 'N/A')}\n"
    response += f"📅 Date of Joining: {emp.get('doj', 'N/A')}\n"
    response += f"🔰 Status: {'Active' if emp.get('status') == 1 else 'Inactive'}\n\n"
    
    # Leave Balance
    if 'error' not in leave_balance:
        response += f"📊 **Leave Balance:** {leave_balance['current_balance']:.1f} days\n"
        response += f"   - Opening Balance: {leave_balance['opening_balance']}\n"
        response += f"   - Leaves Used: {leave_balance['used_leaves']:.1f} days\n\n"
    else:
        response += f"📊 Leave Balance: Data not available\n\n"
    
    # Recent Work Reports
    if work_reports:
        response += f"📋 **Recent Work (Last 7 days):**\n"
        for report in work_reports[:3]:  # Show last 3 reports
            hours = (report['total_time'] or 0) / 3600 if report.get('total_time') else 0
            response += f"   - {report['date']}: {report['task'][:60]}... ({hours:.1f}h)\n"
        response += "\n"
    
    # Recent Leave Requests
    if leave_requests:
        response += f"🏖️  **Recent Leave Requests:**\n"
        for leave in leave_requests[:3]:  # Show last 3 leaves
            status_icon = "✅" if leave['status'] == 'Approved' else "⏳" if leave['status'] in ['Requested', 'Pending'] else "❌"
            response += f"   - {leave['date_of_leave']}: {leave['leave_type']} {status_icon}\n"
    
    return response

@mcp.tool()
def get_leave_balance(name: str, additional_context: Optional[str] = None) -> str:
    """Get detailed leave balance information for an employee"""
    resolution = resolve_employee_ai(name, additional_context)
    
    if resolution['status'] == 'not_found':
        return f"❌ No employee found matching '{name}'."
    
    if resolution['status'] == 'ambiguous':
        options_text = format_employee_options(resolution['employees'])
        return f"🔍 {resolution['message']}\n\n{options_text}"

    emp = resolution['employee']
    leave_balance = get_leave_balance_for_employee(emp['id'])
    
    if 'error' in leave_balance:
        return f"❌ Error retrieving leave balance for {emp['developer_name']}: {leave_balance['error']}"
    
    response = f"📊 **Leave Balance for {emp['developer_name']}**\n\n"
    response += f"💼 Designation: {emp.get('designation', 'N/A')}\n"
    response += f"📧 Email: {emp.get('email_id', 'N/A')}\n\n"
    
    response += f"💰 **Current Balance:** {leave_balance['current_balance']:.1f} days\n"
    response += f"📥 Opening Balance: {leave_balance['opening_balance']} days\n"
    response += f"📤 Leaves Used: {leave_balance['used_leaves']:.1f} days\n\n"
    
    if leave_balance['leave_details']:
        response += f"📋 **Breakdown of Used Leaves:**\n"
        for leave in leave_balance['leave_details']:
            lt = (leave.get('leave_type') or '').upper()
            days_equiv = 1.0 if lt == 'FULL DAY' else 0.5 if lt in ['HALF DAY','COMPENSATION HALF DAY'] else 0.25 if lt in ['2 HRS','COMPENSATION 2 HRS'] else 1.0
            total_days = float(leave.get('count') or 0) * days_equiv
            response += f"   - {leave['leave_type']}: {leave['count']} times ({total_days:.1f} days)\n"
    
    return response

@mcp.tool()
def get_work_report(name: str, days: int = 7, additional_context: Optional[str] = None) -> str:
    """Get work report for an employee for specified number of days"""
    resolution = resolve_employee_ai(name, additional_context)
    
    if resolution['status'] == 'not_found':
        return f"❌ No employee found matching '{name}'."
    
    if resolution['status'] == 'ambiguous':
        options_text = format_employee_options(resolution['employees'])
        return f"🔍 {resolution['message']}\n\n{options_text}"

    emp = resolution['employee']
    work_reports = get_employee_work_report(emp['id'], days)
    
    response = f"📋 **Work Report for {emp['developer_name']}**\n"
    response += f"💼 Designation: {emp.get('designation', 'N/A')}\n"
    response += f"📅 Period: Last {days} days\n\n"
    
    if not work_reports:
        response += "No work reports found for the specified period."
        return response
    
    total_hours = 0.0
    for report in work_reports:
        hours = (report['total_time'] or 0) / 3600 if report.get('total_time') else 0.0
        total_hours += hours
        
        response += f"**{report['date']}** - {report.get('project_name', 'No Project')}\n"
        response += f"Client: {report.get('client_name', 'N/A')}\n"
        response += f"Task: {report['task'][:120]}{'...' if len(report.get('task','')) > 120 else ''}\n"
        if report.get('description'):
            response += f"Details: {report['description'][:120]}{'...' if len(report.get('description','')) > 120 else ''}\n"
        response += f"Hours: {hours:.1f}h\n"
        response += "---\n"
    
    response += f"\n**Total Hours ({days} days): {total_hours:.1f}h**\n"
    response += f"Average per day: { (total_hours/days):.1f}h" if days > 0 else ""
    
    return response

@mcp.tool()
def get_leave_history(name: str, additional_context: Optional[str] = None) -> str:
    """Get leave history for an employee"""
    resolution = resolve_employee_ai(name, additional_context)
    
    if resolution['status'] == 'not_found':
        return f"❌ No employee found matching '{name}'."
    
    if resolution['status'] == 'ambiguous':
        options_text = format_employee_options(resolution['employees'])
        return f"🔍 {resolution['message']}\n\n{options_text}"

    emp = resolution['employee']
    leave_requests = get_employee_leave_requests(emp['id'], limit=100)
    
    response = f"🏖️  **Leave History for {emp['developer_name']}**\n"
    response += f"💼 Designation: {emp.get('designation', 'N/A')}\n\n"
    
    if not leave_requests:
        response += "No leave requests found."
        return response
    
    approved_count = sum(1 for lr in leave_requests if lr['status'] == 'Approved')
    pending_count = sum(1 for lr in leave_requests if lr['status'] in ['Requested', 'Pending'])
    declined_count = sum(1 for lr in leave_requests if lr['status'] == 'Declined')
    
    response += f"📊 Summary: {approved_count} Approved, {pending_count} Pending, {declined_count} Declined\n\n"
    
    for leave in leave_requests[:40]:
        status_icon = "✅" if leave['status'] == 'Approved' else "⏳" if leave['status'] in ['Requested', 'Pending'] else "❌"
        response += f"**{leave['date_of_leave']}** - {leave['leave_type']} {status_icon}\n"
        if leave.get('dev_comments'):
            response += f"Reason: {leave['dev_comments']}\n"
        if leave.get('admin_comments') and leave['status'] != 'Pending':
            response += f"Admin Note: {leave['admin_comments']}\n"
        response += "---\n"
    
    return response

@mcp.tool()
def search_employees(search_query: str) -> str:
    """Search for employees by name, designation, email, or employee number"""
    employees = fetch_employees_ai(search_term=search_query)
    
    if not employees:
        return f"❌ No employees found matching '{search_query}'"
    
    response = f"🔍 **Search Results for '{search_query}':**\n\n"
    
    for i, emp in enumerate(employees, 1):
        response += f"{i}. **{emp['developer_name']}**\n"
        response += f"   💼 {emp.get('designation', 'N/A')}\n"
        response += f"   📧 {emp.get('email_id', 'N/A')}\n"
        response += f"   📞 {emp.get('mobile', 'N/A')}\n"
        response += f"   🆔 {emp.get('emp_number', 'N/A')}\n"
        response += f"   🔰 {'Active' if emp.get('status') == 1 else 'Inactive'}\n"
        
        # Get quick leave balance
        try:
            leave_balance = get_leave_balance_for_employee(emp['id'])
            if 'error' not in leave_balance:
                response += f"   📊 Leave Balance: {leave_balance['current_balance']:.1f} days\n"
        except Exception:
            pass
        
        response += "\n"
    
    return response

# -------------------------------
# New HR-specific tools
# -------------------------------

@mcp.tool()
def get_employee_profile(name: str, additional_context: Optional[str] = None) -> str:
    """Return extended HR profile (documents, PF status, confirmation, etc.)"""
    resolution = resolve_employee_ai(name, additional_context)
    if resolution['status'] != 'resolved':
        if resolution['status'] == 'ambiguous':
            return f"🔍 Ambiguous: \n\n{format_employee_options(resolution['employees'])}"
        return f"❌ No employee found matching '{name}'."

    emp = resolution['employee']
    # Build profile
    response = f"📇 **HR Profile: {emp['developer_name']}**\n"
    response += f"🆔 ID: {emp['id']}  |  Emp#: {emp.get('emp_number','N/A')}\n"
    response += f"💼 Designation: {emp.get('designation','N/A')}\n"
    response += f"📅 DOJ: {emp.get('doj','N/A')}  |  Confirmation Date: {emp.get('confirmation_date','N/A') if 'confirmation_date' in emp else 'N/A'}\n"
    response += f"🏥 PF Enabled: {'Yes' if emp.get('is_pf_enabled') in [1,'1',True] else 'No'}\n"
    response += f"📧 Work Email: {emp.get('email_id','N/A')}  |  Personal Email: {emp.get('personal_emaill','N/A') if 'personal_emaill' in emp else 'N/A'}\n"
    response += f"📞 Mobile: {emp.get('mobile','N/A')}  |  Emergency Contact: {emp.get('emergency_contact_name','N/A')} ({emp.get('emergency_contact_no','N/A')})\n\n"

    # Documents urls if present (show placeholders)
    doc_keys = ['pan_front','pan_back','aadhar_front','aadhar_back','degree_front','degree_back']
    docs_present = []
    for k in doc_keys:
        if emp.get(k):
            docs_present.append(k)
    if docs_present:
        response += f"🗂️ Documents available: {', '.join(docs_present)}\n"
    else:
        response += "🗂️ No HR document images found.\n"

    # Opening leave + PF join date
    if 'opening_leave_balance' in emp:
        try:
            response += f"📊 Opening Leave Balance: {float(emp.get('opening_leave_balance') or 0):.1f} days\n"
        except Exception:
            pass
    if emp.get('pf_join_date'):
        response += f"📌 PF Join Date: {emp.get('pf_join_date')}\n"

    return response

@mcp.tool()
def get_appraisal_feedback(name: str, additional_context: Optional[str] = None, limit: int = 5) -> str:
    """Get recent positive/negative feedback for an employee"""
    resolution = resolve_employee_ai(name, additional_context)
    if resolution['status'] != 'resolved':
        if resolution['status'] == 'ambiguous':
            return f"🔍 Ambiguous: \n\n{format_employee_options(resolution['employees'])}"
        return f"❌ No employee found matching '{name}'"

    emp = resolution['employee']
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT project_name, feedback_type, date_of_incident, comments
            FROM appraisal_feedback
            WHERE developer_id = %s
            ORDER BY date_of_incident DESC
            LIMIT %s
        """, (emp['id'], int(limit)))
        feedbacks = cursor.fetchall()

        if not feedbacks:
            return f"ℹ️ No appraisal feedback found for {emp['developer_name']}."

        response = f"🗂️ **Appraisal Feedback for {emp['developer_name']}**\n\n"
        for fb in feedbacks:
            icon = "👍" if (fb.get('feedback_type') or "").upper() == "POSITIVE" else "👎"
            response += f"{icon} **{fb.get('project_name','-')}** ({fb.get('date_of_incident','-')})\n"
            if fb.get('comments'):
                response += f"💬 {fb.get('comments')}\n"
            response += "---\n"
        return response
    except Exception as e:
        return f"❌ Error fetching appraisal feedback: {e}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_incentives(name: str, additional_context: Optional[str] = None) -> str:
    """Retrieve incentive earnings for an employee"""
    resolution = resolve_employee_ai(name, additional_context)
    if resolution['status'] != 'resolved':
        if resolution['status'] == 'ambiguous':
            return f"🔍 Ambiguous: \n\n{format_employee_options(resolution['employees'])}"
        return f"❌ No employee found matching '{name}'"

    emp = resolution['employee']
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT ie.id, ie.incentive, ie.remarks, ps.project_name, ie.added_at
            FROM incentive_earned ie
            LEFT JOIN project_settings ps ON ie.project_settings_id = ps.id
            WHERE ie.user_id = %s
            ORDER BY ie.added_at DESC
            LIMIT 20
        """, (emp['id'],))
        rows = cursor.fetchall()
        if not rows:
            return f"ℹ️ No incentives recorded for {emp['developer_name']}."

        total = sum(float(r.get('incentive') or 0) for r in rows)
        response = f"💸 **Incentives for {emp['developer_name']}** — Total last entries: {len(rows)}\n"
        response += f"🏷️ Sum: {total:.2f}\n\n"
        for r in rows[:10]:
            response += f"• {r.get('project_name','-')} — {r.get('incentive',0):.2f} ({r.get('added_at')})\n"
            if r.get('remarks'):
                response += f"  _{r.get('remarks')}_\n"
        return response
    except Exception as e:
        return f"❌ Error retrieving incentives: {e}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_attendance_summary(name: str, days: int = 30, additional_context: Optional[str] = None) -> str:
    """
    Summarize attendance/presence using work_report entries and approved leaves.
    Heuristic: days with work_report logged count as present. Approved full-day leaves count as present (or as leave).
    """
    resolution = resolve_employee_ai(name, additional_context)
    if resolution['status'] != 'resolved':
        if resolution['status'] == 'ambiguous':
            return f"🔍 Ambiguous: \n\n{format_employee_options(resolution['employees'])}"
        return f"❌ No employee found matching '{name}'"
    emp = resolution['employee']
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # work_report days
        cursor.execute("""
            SELECT DISTINCT date FROM work_report
            WHERE developer_id = %s AND date >= %s AND date <= %s
        """, (emp['id'], start_date, end_date))
        work_days = {r['date'] for r in cursor.fetchall() if r.get('date')}
        # approved leaves
        cursor.execute("""
            SELECT date_of_leave, leave_type FROM leave_requests
            WHERE developer_id = %s AND status = 'Approved' AND date_of_leave >= %s AND date_of_leave <= %s
        """, (emp['id'], start_date, end_date))
        leaves = cursor.fetchall()
        leave_days = [l['date_of_leave'] for l in leaves if l.get('date_of_leave')]

        total_days = (end_date - start_date).days + 1
        present_days = len(work_days)
        approved_leave_days = len(set(leave_days))
        absent_or_missing = total_days - (present_days + approved_leave_days)

        response = f"📅 **Attendance Summary for {emp['developer_name']}**\n"
        response += f"Period: {start_date} to {end_date} ({total_days} days)\n"
        response += f"✅ Present (work_report): {present_days} days\n"
        response += f"🏖️ Approved Leaves: {approved_leave_days} days\n"
        response += f"❗Absent/Missing logs: {absent_or_missing} days\n"
        return response
    except Exception as e:
        return f"❌ Error generating attendance summary: {e}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_pf_status(name: str, additional_context: Optional[str] = None) -> str:
    """Check PF status and PF join / releiving dates"""
    resolution = resolve_employee_ai(name, additional_context)
    if resolution['status'] != 'resolved':
        if resolution['status'] == 'ambiguous':
            return f"🔍 Ambiguous: \n\n{format_employee_options(resolution['employees'])}"
        return f"❌ No employee found matching '{name}'"
    emp = resolution['employee']
    response = f"🏦 **PF Status for {emp['developer_name']}**\n"
    response += f"PF Enabled: {'Yes' if emp.get('is_pf_enabled') in [1,'1',True] else 'No'}\n"
    response += f"PF Join Date: {emp.get('pf_join_date','N/A')}\n"
    response += f"Releiving Date: {emp.get('releiving_date','N/A') if 'releiving_date' in emp else 'N/A'}\n"
    return response

# -------------------------------
# Company Management Activities
# -------------------------------
@mcp.tool()
def get_client_list(active_only: bool = True) -> str:
    """List clients with contact details"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if active_only:
            cursor.execute("SELECT id, client_name, company_name, contact_person, email_id, phone, status FROM client WHERE status = 1 ORDER BY client_name")
        else:
            cursor.execute("SELECT id, client_name, company_name, contact_person, email_id, phone, status FROM client ORDER BY client_name")
        rows = cursor.fetchall()
        if not rows:
            return "ℹ️ No clients found."

        response = "👥 **Clients**\n\n"
        for r in rows[:50]:
            response += f"• {r.get('client_name')} — {r.get('company_name')}\n"
            response += f"   Contact: {r.get('contact_person') or 'N/A'} — {r.get('email_id') or 'N/A'} — {r.get('phone') or 'N/A'}\n"
            response += f"   Status: {'Active' if r.get('status') == 1 else 'Inactive'}\n\n"
        return response
    except Exception as e:
        return f"❌ Error fetching clients: {e}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_projects_overview(active_only: bool = True) -> str:
    """Show active (or all) projects with client info"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if active_only:
            cursor.execute("""
                SELECT p.id, p.title, p.status, c.client_name, c.email_id
                FROM project p
                LEFT JOIN client c ON p.client_id = c.id
                WHERE p.status = 1
                ORDER BY p.date DESC
            """)
        else:
            cursor.execute("""
                SELECT p.id, p.title, p.status, c.client_name, c.email_id
                FROM project p
                LEFT JOIN client c ON p.client_id = c.id
                ORDER BY p.date DESC
            """)
        projects = cursor.fetchall()
        if not projects:
            return "❌ No projects found."

        response = "🏗️ **Projects Overview**\n\n"
        for proj in projects[:100]:
            response += f"📌 {proj.get('title')} (ID: {proj.get('id')})\n"
            response += f"   Client: {proj.get('client_name') or 'N/A'} — {proj.get('email_id') or 'N/A'}\n"
            response += f"   Status: {'Active' if proj.get('status') == 1 else 'Inactive'}\n\n"
        return response
    except Exception as e:
        return f"❌ Error fetching projects: {e}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_project_status_updates(project_settings_id: Optional[int] = None, limit: int = 20) -> str:
    """Fetch milestone progress & completion percentage"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if project_settings_id:
            cursor.execute("""
                SELECT ps.id as project_settings_id, ps.project_name, ps.project_id, ps.current_milestone_id,
                       ps.total_estimated_hrs, ps.is_incentive_enabled,
                       pu.user_id as updated_by, ps.added_at
                FROM project_settings ps
                LEFT JOIN project_status_updates pu ON pu.project_settings_id = ps.id
                WHERE ps.id = %s
                LIMIT %s
            """, (project_settings_id, limit))
            rows = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT ps.id as project_settings_id, ps.project_name, ps.project_id, ps.current_milestone_id,
                       ps.total_estimated_hrs, ps.is_incentive_enabled,
                       pu.user_id as updated_by, pu.required_hours, pu.per_completed, pu.added_at
                FROM project_settings ps
                LEFT JOIN project_status_updates pu ON pu.project_settings_id = ps.id
                ORDER BY pu.added_at DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()

        if not rows:
            return "ℹ️ No project status updates found."

        response = "🔄 **Project Status Updates**\n\n"
        for r in rows[:limit]:
            response += f"• Project: {r.get('project_name','-')} (Settings ID: {r.get('project_settings_id')})\n"
            if r.get('required_hours') is not None:
                response += f"   Required Hours: {r.get('required_hours')} | Completed%: {r.get('per_completed')}\n"
            response += f"   Milestone: {r.get('current_milestone_id') or '-'} | Total Est Hrs: {r.get('total_estimated_hrs') or 0}\n"
            response += f"   Updated at: {r.get('added_at')}\n\n"
        return response
    except Exception as e:
        return f"❌ Error fetching project status updates: {e}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_payments_summary(period_months: int = 12) -> str:
    """View total payments received & missed invoices summary for last N months"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cutoff = date.today() - timedelta(days=30*period_months)
        cursor.execute("""
            SELECT SUM(amount) as total_received, COUNT(*) as count_received
            FROM payments_received
            WHERE added_at >= %s
        """, (cutoff,))
        rec = cursor.fetchone() or {}
        total_received = float(rec.get('total_received') or 0)
        count_received = int(rec.get('count_received') or 0)

        cursor.execute("""
            SELECT status, COUNT(*) as cnt, SUM(amount) as total_amount
            FROM missed_invoices
            WHERE added_at >= %s
            GROUP BY status
        """, (cutoff,))
        invoices = cursor.fetchall()

        response = f"💰 **Payments Summary (last {period_months} months)**\n"
        response += f"Total Received: {total_received:.2f} across {count_received} payments\n\n"
        if invoices:
            response += "Missed/Other Invoices:\n"
            for inv in invoices:
                response += f" • {inv.get('status')}: {inv.get('cnt')} invoices — Total: {float(inv.get('total_amount') or 0):.2f}\n"
        else:
            response += "No missed invoices in the period.\n"
        return response
    except Exception as e:
        return f"❌ Error computing payments summary: {e}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_fixed_expenses(project_id: Optional[str] = None) -> str:
    """Retrieve company/project-level fixed expenses"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if project_id:
            cursor.execute("SELECT id, project_id, purpose, amount, added_at FROM fixed_expenses WHERE project_id = %s ORDER BY added_at DESC LIMIT 100", (project_id,))
        else:
            cursor.execute("SELECT id, project_id, purpose, amount, added_at FROM fixed_expenses ORDER BY added_at DESC LIMIT 100")
        rows = cursor.fetchall()
        if not rows:
            return "ℹ️ No fixed expenses found."

        total = sum(float(r.get('amount') or 0) for r in rows)
        response = f"🧾 **Fixed Expenses** — Entries: {len(rows)} — Total: {total:.2f}\n\n"
        for r in rows[:50]:
            response += f"• Project: {r.get('project_id')} — {r.get('purpose')} — {r.get('amount'):.2f} ({r.get('added_at')})\n"
        return response
    except Exception as e:
        return f"❌ Error fetching fixed expenses: {e}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_holidays(upcoming_days: int = 90) -> str:
    """List upcoming company holidays"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        today = date.today()
        end = today + timedelta(days=upcoming_days)
        cursor.execute("""
            SELECT occasion, holiday_date
            FROM holidays
            WHERE holiday_date >= %s AND holiday_date <= %s
            ORDER BY holiday_date ASC
        """, (today, end))
        rows = cursor.fetchall()
        if not rows:
            return f"ℹ️ No holidays in the next {upcoming_days} days."

        response = f"🎉 **Upcoming Holidays (next {upcoming_days} days)**\n"
        for r in rows[:100]:
            response += f"• {r.get('holiday_date')} — {r.get('occasion')}\n"
        return response
    except Exception as e:
        return f"❌ Error fetching holidays: {e}"
    finally:
        cursor.close()
        conn.close()

# -------------------------------
# MCP Endpoint + Health
# -------------------------------
@mcp.custom_route("/mcp", methods=["POST"])
async def mcp_endpoint(request: Request):
    """MCP protocol endpoint"""
    return JSONResponse({"status": "MCP server is running"})

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    return JSONResponse({
        "message": "Leave Manager + HR + Company Management MCP Server",
        "status": "running",
        "version": "1.0.0"
    })

# -------------------------------
# Run MCP server
# -------------------------------
if __name__ == "__main__":
    if Levenshtein is None:
        print("Warning: python-levenshtein not installed. Fuzzy quality will be slightly lower. Install with: pip install python-Levenshtein")

    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))

    print(f"Starting Leave Manager Plus MCP Server on {host}:{port} with {transport} transport")
    mcp.run(transport=transport, host=host, port=port)
