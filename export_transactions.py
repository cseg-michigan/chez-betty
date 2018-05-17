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
sheet_overview.set_column(1, 1, 20)
sheet_banktransfer.write('C1', 'Amount', bold)
sheet_banktransfer.write('D1', 'Type', bold)
# When the "safe" was introduced to Betty software
BANKTRANSFER_CUTOVER_TIME = arrow.get(2016, 4, 14)
banktransfer_row = 1

with bootstrap('development.ini') as env:
    for transaction_type, explanation in (
            ('purchase', 'Money from user balance. Does not represent cash received. Does represent inventory removed'),
            ('deposit', 'Actual money from user into Betty.'),
            ('cashdeposit', 'Money *reported by users* into Betty'),
            ('ccdeposit', 'Actual money from user into Betty (via Credit Card).'),
            ('btcdeposit', 'Actual money from user into Betty (via BitCoin).'),
            ('adjustment', 'Catch-all for corrections/fixes/manual intervention'),
            ('restock', 'Actual money paid out to suppliers for Betty inventory'),
            ('inventory', 'Value of inventory lost or found when physical inventory counted'),
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
        sheet.write('D1', 'Notes', bold)
        sheet.set_column(3, 3, 100)

        row = 1
        for t in reversed(transactions):
            sheet.write_number(row, 0, t.id)
            sheet.write_datetime(row, 1, t.event.timestamp.datetime, date_format)
            sheet.write_number(row, 2, t.amount, money_format)
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

        sheet_overview.write(overview_row, 0, transaction_type)
        sheet_overview.write_formula(overview_row, 1,
                '=SUM({}!C:C)'.format(transaction_type), money_format)
        sheet_overview.write(overview_row, 2, explanation)
        overview_row += 1

sheet_overview.write(overview_row, 0, 'loans')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Startup funds loaned to Betty (liability)')
overview_row += 1

sheet_overview.write(overview_row, 0, 'CashDeposits')
sheet_overview.write_number(overview_row, 1, 0, money_format)
sheet_overview.write(overview_row, 2, 'Actual money put into the bank')
overview_row += 1

overview_row += 3
sheet_overview.write(overview_row, 0, 'Actual Income')
sheet_overview.write_formula(overview_row, 1, '=SUM(B5,B6,B18,B14)', money_format)
sheet_overview.write(overview_row, 2, 'Money that hit the bank account (CC and BTC deposits, plus actual cash in cashbox/safe, plus donations)')
overview_row += 1
sheet_overview.write(overview_row, 0, 'User Liabilities')
sheet_overview.write_formula(overview_row, 1, '=SUM(B4,B5,B6)-B2', money_format)
sheet_overview.write(overview_row, 2, 'Money in user accounts not yet spent (Cash/CC/BTC deposits - purchases)')
overview_row += 1
sheet_overview.write(overview_row, 0, 'Actual Outflow')
sheet_overview.write_formula(overview_row, 1, '=SUM(B7,B8,B15)', money_format)
sheet_overview.write(overview_row, 2, 'Money that left the bank account (restock + withdrawl)')

workbook.close()
