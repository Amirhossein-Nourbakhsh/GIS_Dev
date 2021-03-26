import os,sys

# reference path to break down
# r'\\10.6.246.73\Sanborn\New York City\Brooklyn\1990 - 1969\Volume 12'
gs_fim_directory = r'\\10.6.246.73\Sanborn'

for state in os.listdir(gs_fim_directory):
    
state = ''
year_range = ''
year = ''
Volume = ''
number_of_sheets = 0
sheet_numbers = []