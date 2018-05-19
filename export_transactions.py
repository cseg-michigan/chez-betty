#!./venv/bin/python

# https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/commandline.html#writing-a-script
from pyramid.paster import bootstrap

# Betty imports
from chezbetty.models.event import Event
from chezbetty.models.transaction import Transaction
from chezbetty.models.user import User

# General Python
import sys

import arrow
import xlsxwriter




year = int(sys.argv[1])
assert(year >= 2014)

START = arrow.get(year, 7, 1)
END = arrow.get(year+1, 7, 1)
#END = arrow.get(2014, 8, 1)

workbook = xlsxwriter.Workbook('records-{}.xlsx'.format(year), {'remove_timezone': True})

# Add a bold format to use to highlight cells.
bold = workbook.add_format({'bold': True})

# Add a number format for cells with money.
money_format = workbook.add_format({'num_format': '$#,##0.00'})

# Add an Excel date format.
date_format = workbook.add_format({'num_format': 'mmmm d yyyy hh:mm'})

sheet_overview = workbook.add_worksheet('Overview')
sheet_overview.write('A1', 'Type', bold)
sheet_overview.write('B1', 'Total', bold)
sheet_overview.write('C1', 'Explanation', bold)
sheet_overview.set_column(0, 1, 15)
sheet_overview.set_column(2, 2, 100)
overview_row = 1

sheet_banktransfer = workbook.add_worksheet('CashDeposits')
sheet_banktransfer.write('A1', 'Id', bold)
sheet_banktransfer.write('B1', 'Date', bold)
sheet_banktransfer.set_column(1, 1, 20)
sheet_banktransfer.write('C1', 'Amount', bold)
sheet_banktransfer.write('D1', 'Type', bold)
# When the "safe" was introduced to Betty software
BANKTRANSFER_CUTOVER_TIME = arrow.get(2016, 4, 14)
banktransfer_row = 1

sheet_charitable = workbook.add_worksheet('charitable')
sheet_charitable.write('A1', 'Id', bold)
sheet_charitable.write('B1', 'Date', bold)
sheet_charitable.set_column(1, 1, 20)
sheet_charitable.write('C1', 'Amount', bold)
sheet_charitable.write('D1', 'Type', bold)

cell = {}

with bootstrap('development.ini') as env:
    for transaction_type, explanation in (
            ('purchase', 'Money from user balance. Does not represent cash received. Does represent inventory removed'),
            ('deposit', 'Actual money from user into Betty.'),
            ('cashdeposit', 'Money *reported by users* into Betty'),
            ('ccdeposit', 'Actual money from user into Betty (via Credit Card).'),
            ('btcdeposit', 'Actual money from user into Betty (via BitCoin).'),
            ('adjustment', 'Catch-all for corrections/fixes/manual intervention'),
            ('restock', 'Actual money paid out to suppliers for Betty inventory'),
            ('inventory', 'Value of inventory lost when physical inventory counted'),
            ('emptycashbox', 'Money removed from the cashbox'),
            ('emptysafe', 'Money removed from the safe'),
            ('lost', 'Money expected in the cashbox/safe that was missing'),
            ('found', 'More money was in the cashbox/safe than expected'),
            ('donation', 'Money given to Betty'),
            ('withdrawal', 'Money removed from Betty for expenses'),
            ('reimbursement', 'Money removed from bank account for reimbursement'),
            ):
        transactions = Transaction.all(start=START, end=END, trans_type=transaction_type)

        sheet = workbook.add_worksheet(transaction_type)
        sheet.write('A1', 'Id', bold)
        sheet.write('B1', 'Date', bold)
        sheet.set_column(1, 1, 20)
        sheet.write('C1', 'Amount', bold)
        if transaction_type == 'purchase':
            sheet.write('D1', 'Wholesale', bold)
        else:
            sheet.write('D1', 'Notes', bold)
            sheet.set_column(3, 3, 100)

        row = 1
        for t in reversed(transactions):
            # Ignore initial capital "donation"s
            if t.id == 1485 or t.id == 2053:
                continue

            sheet.write_number(row, 0, t.id)
            sheet.write_datetime(row, 1, t.event.timestamp.datetime, date_format)
            sheet.write_number(row, 2, t.amount, money_format)
            if transaction_type == 'purchase':
                wholesale = 0
                for line_item in t.subtransactions:
                    wholesale += line_item.wholesale
                sheet.write_number(row, 3, wholesale, money_format)
            else:
                sheet.write(row, 3, t.event.notes)
            row += 1

            if transaction_type == 'emptycashbox' and t.event.timestamp < BANKTRANSFER_CUTOVER_TIME:
                sheet_banktransfer.write_number(banktransfer_row, 0, t.id)
                sheet_banktransfer.write_datetime(banktransfer_row, 1, t.event.timestamp.datetime, date_format)
                sheet_banktransfer.write_number(banktransfer_row, 2, t.amount, money_format)
                sheet_banktransfer.write(banktransfer_row, 3, "cashbox")
                banktransfer_row += 1
            if transaction_type == 'emptysafe':
                sheet_banktransfer.write_number(banktransfer_row, 0, t.id)
                sheet_banktransfer.write_datetime(banktransfer_row, 1, t.event.timestamp.datetime, date_format)
                sheet_banktransfer.write_number(banktransfer_row, 2, t.amount, money_format)
                sheet_banktransfer.write(banktransfer_row, 3, "safe")
                banktransfer_row += 1

        cell[transaction_type] = 'B{}'.format(overview_row+1)
        sheet_overview.write(overview_row, 0, transaction_type)
        sheet_overview.write_formula(overview_row, 1,
                '=SUM({}!C:C)'.format(transaction_type), money_format)
        sheet_overview.write(overview_row, 2, explanation)
        overview_row += 1
        if transaction_type == 'purchase':
            cell['purchase_wholesale'] = 'B{}'.format(overview_row+1)
            sheet_overview.write(overview_row, 0, 'purchase_wholesale')
            sheet_overview.write_formula(overview_row, 1,
                    '=SUM({}!D:D)'.format(transaction_type), money_format)
            sheet_overview.write(overview_row, 2, 'wholesale cost of purchases')
            overview_row += 1

cell['CashDeposits'] = 'B{}'.format(overview_row+1)
sheet_overview.write(overview_row, 0, 'CashDeposits')
sheet_overview.write_formula(overview_row, 1, '=SUM(CashDeposits!C:C)', money_format)
sheet_overview.write(overview_row, 2, 'Actual money put into the bank')
overview_row += 1

cell['charitable'] = 'B{}'.format(overview_row+1)
sheet_overview.write(overview_row, 0, 'charitable')
sheet_overview.write_formula(overview_row, 1, '=SUM(charitable!C:C)', money_format)
sheet_overview.write(overview_row, 2, 'Donations from Betty to CSEG')
overview_row += 1

overview_row += 3
sheet_overview.write(overview_row, 0, 'Actual Income')
sheet_overview.write_formula(overview_row, 1,
        '=SUM({},{},{},{})'.format(cell['ccdeposit'], cell['btcdeposit'], cell['CashDeposits'], cell['donation']), money_format)
sheet_overview.write(overview_row, 2, 'Money that hit the bank account (CC and BTC deposits, plus actual cash in cashbox/safe, plus donations)')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Accrued Income')
sheet_overview.write_formula(overview_row, 1,
        '=SUM({},{},{},{})'.format(cell['cashdeposit'], cell['ccdeposit'], cell['btcdeposit'], cell['donation']), money_format)
sheet_overview.write(overview_row, 2, 'Money that should hit the bank account (User-reported cash, CC and BTC deposits, plus donations)')
overview_row += 1
sheet_overview.write(overview_row, 0, 'User Liabilities')
sheet_overview.write_formula(overview_row, 1,
        '=SUM({},{},{})-{}'.format(cell['cashdeposit'], cell['ccdeposit'], cell['btcdeposit'], cell['purchase']), money_format)
sheet_overview.write(overview_row, 2, 'Money in user accounts not yet spent (Cash/CC/BTC deposits - purchases)')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Actual Outflow')
sheet_overview.write_formula(overview_row, 1,
        '=SUM({},{},{})'.format(cell['adjustment'], cell['restock'], cell['withdrawal']), money_format)
sheet_overview.write(overview_row, 2, 'Money that left the bank account (adjustment + restock + withdrawal)')


########################################
## Begin Form 1125-A
overview_row += 3
sheet_overview.write(overview_row, 0, 'Form 1125-A', bold)
overview_row += 1
sum_start = overview_row
cell['inventory_beginning'] = 'B{}'.format(overview_row+1)
sheet_overview.write(overview_row, 0, 'Box 1')
sheet_overview.write(overview_row, 2, 'Get from prior year Line 7')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 2')
sheet_overview.write_formula(overview_row, 1, '='+cell['restock'], money_format)
sheet_overview.write(overview_row, 2, 'Purchases')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 3')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Cost of Labor')
overview_row += 1
# Resellers with less than $10Million average over the last three years
sheet_overview.write(overview_row, 0, 'Box 4')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Section 263A costs')
overview_row += 1
sum_end = overview_row
sheet_overview.write(overview_row, 0, 'Box 5')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Other costs')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 6')
sheet_overview.write_formula(overview_row, 1,
        '=SUM(B{}:B{})'.format(sum_start+1,sum_end+1), money_format)
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 7')
sheet_overview.write_formula(overview_row, 1,
        '=' + cell['inventory_beginning'] + '+' + cell['restock'] + '-' + cell['purchase_wholesale'] + '-' + cell['inventory'], money_format)
sheet_overview.write(overview_row, 2, 'Inventory from the year is sum restocks less wholesale purchase values less inventory losses')
overview_row += 1
cell['COGS'] = 'B{}'.format(overview_row+1)
sheet_overview.write(overview_row, 0, 'Box 8')
sheet_overview.write_formula(overview_row, 1,
        '=B{}-B{}'.format(overview_row-2+1,overview_row-1+1), money_format)
sheet_overview.write(overview_row, 2, 'Cost of goods sold')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 9')
sheet_overview.write(overview_row, 2, 'Check 9a(i) [Cost], 9b-d blank, 9e and 9f check No')



########################################
## Begin Form 1120
overview_row += 3
sheet_overview.write(overview_row, 0, 'Form 1120', bold)
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 1a')
sheet_overview.write_formula(overview_row, 1, '='+cell['purchase'], money_format)
sheet_overview.write(overview_row, 2, 'Gross receipts or sales')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 1b')
sheet_overview.write_number(overview_row, 1, 0, money_format)
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 1c')
sheet_overview.write_formula(overview_row, 1, '='+cell['purchase'], money_format)
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 2')
sheet_overview.write_formula(overview_row, 1, '='+cell['COGS'], money_format)
sheet_overview.write(overview_row, 2, 'Cost of goods sold')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 3')
sum_start = overview_row
sheet_overview.write_formula(overview_row, 1,
        '=B{}-B{}'.format(overview_row-2+1,overview_row-1+1), money_format)
sheet_overview.write(overview_row, 2, 'Gross profit')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 4')
sheet_overview.write_number(overview_row, 1, 0, money_format)
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 5')
sheet_overview.write_number(overview_row, 1, 0, money_format)
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 6')
sheet_overview.write_number(overview_row, 1, 0, money_format)
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 7')
sheet_overview.write_number(overview_row, 1, 0, money_format)
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 8')
sheet_overview.write_number(overview_row, 1, 0, money_format)
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 9')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Form 4797: Sales of Business Property')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 10')
sum_end = overview_row
sheet_overview.write_formula(overview_row, 1,
        '={}+{}'.format(cell['found'], cell['donation']), money_format)
sheet_overview.write(overview_row, 2, 'Other income. Attach Schedule. DO THIS')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 11')
cell['total_income'] = 'B{}'.format(overview_row+1)
sheet_overview.write_formula(overview_row, 1,
        '=SUM(B{}:B{})'.format(sum_start+1,sum_end+1), money_format)
sheet_overview.write(overview_row, 2, 'Total income')

overview_row += 1
sum_start = overview_row
sheet_overview.write(overview_row, 0, 'Box 12')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Compensation of officers')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 13')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Salaries and wages')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 14')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Repairs and maintenance. No machinery/big things, careful do not double-count')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 15')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'We could do this, but then would also have to do the flip side (absorbed user balances). Easier to leave all outstanding.')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 16')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Rents. (Includes vehicle rentals)')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 17')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Taxes and licenses. Do not include sales tax.')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 18')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Interest (from debts).')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 19')
#Need to calculate later with 10% cap
#sheet_overview.write_formula(overview_row, 1,
#        '={}'.format(cell['charitable']), money_format)
sheet_overview.write(overview_row, 2, 'Charitable contributions.')
charitable_row = overview_row
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 20')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Depreciation of assets.')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 21')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Depletion (of natural deposits).')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 22')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Advertising.')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 23')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Pension/profit-sharing/etc.')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 24')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Employee Benefit Programs.')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 25')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Domestic production deduction.')
overview_row += 1
sum_end = overview_row
sheet_overview.write(overview_row, 0, 'Box 26')
sheet_overview.write_formula(overview_row, 1,
        '={}+{}'.format(cell['lost'], cell['withdrawal']), money_format)
sheet_overview.write(overview_row, 2, 'Other deductions (attach statement) DO THIS.')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 27')
cell['total_deductions'] = 'B{}'.format(overview_row+1)
sheet_overview.write_formula(overview_row, 1,
        '=SUM(B{}:B{})'.format(sum_start+1,sum_end+1), money_format)
sheet_overview.write(overview_row, 2, 'Total deductions')
sheet_overview.write_formula(overview_row, 3,
        '=SUM(B{}:B{}) + SUM(B{}:B{})'.format(
            sum_start+1,charitable_row-1+1,
            charitable_row+1+1,sum_end+1), money_format)
cell['total_deductions_no_charitable'] = 'D{}'.format(overview_row+1)
sheet_overview.write(overview_row, 4, 'Deductions except charitable')

overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 28')
sheet_overview.write_formula(overview_row, 1,
        '=' + cell['total_income'] + '-' + cell['total_deductions'], money_format)
sheet_overview.write(overview_row, 2, 'Taxable income before NOL')
sheet_overview.write_formula(overview_row, 3,
        '=' + cell['total_income'] + '-' + cell['total_deductions_no_charitable'], money_format)
sheet_overview.write(overview_row, 4, 'Taxable income except charitable')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 29abc')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Net operating losses (NOL).')
sheet_overview.write_formula(overview_row, 3,
        '=0.1*D{}'.format(overview_row-1+1), money_format)
sheet_overview.write(overview_row, 4, '10% taxable income except charitable')
cell['charitable_cap'] = 'D{}'.format(overview_row+1)
#Late-calculate charitable
sheet_overview.write_formula(charitable_row, 1,
        '=MIN({},{})'.format(cell['charitable'],cell['charitable_cap']), money_format)

overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 30')
sheet_overview.write_formula(overview_row, 1,
        '=B{}-B{}'.format(overview_row-2+1,overview_row-1+1), money_format)
sheet_overview.write(overview_row, 2, 'Taxable income.')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Box 31')
sheet_overview.write_formula(overview_row, 1,
        '=B{} * 0.15'.format(overview_row-1+1), money_format)
sheet_overview.write(overview_row, 2, 'CHECK INSTRUCTIONS / do J: 15% for <$50k and no deductions assumed')


workbook.close()
