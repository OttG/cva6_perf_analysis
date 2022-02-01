#filename = os.path.basename(dis_file.name)
#filename = filename.replace('_dis.s','')

import pdb
import os
import os.path
import numpy as np
import xlsxwriter

perf_counters = ['pc_cycles', 'pc_instr', 'pc_icache_miss', 'pc_dcache_miss', 'pc_load', 'pc_store', 'pc_exception', 'pc_excepetion_ret', 'pc_branch_jump', 'pc_call', 'pc_returns', 'pc_mispredict', 'pc_sb_full', 'pc_fetch_fifo_empty' ]

inactivity_counters = ['total_inactivity', 'register_unavailable', \
                       'rs_load', 'rs_store', 'rs_alu', 'rs_ctrl_flow', 'rs_csr', 'rs_mult', 'rs_fpu', \
                       'scoreboard_full', 'waw', 'multb2b', 'fu_busy', \
                       'fu_load_store', 'fu_flu', 'fu_fpu' ]

miss_prediction_counters = ['Total Resolved branches', 'BHT', 'RAS', 'BTB']

# Get the log files from the traces folder
script_path         = os.getcwd()
traces_path         = os.path.join(script_path + os.sep + 'traces'     )
disassembly_path    = os.path.join(script_path + os.sep + 'disassembly')
logs_path           = os.path.join(script_path + os.sep + 'logs'       )

test_traces_list    = [f for f in os.listdir(traces_path) if (os.path.isfile(os.path.join(traces_path + os.sep + f)) & ('-trace.log' in f))]
traces_list_path    = [os.path.join(traces_path + os.sep + f) for f in test_traces_list]

logs_list      = [f for f in os.listdir(logs_path) if (os.path.isfile(os.path.join(logs_path + os.sep + f)) & ('-run.log' in f))]
logs_list_path = [os.path.join(logs_path + os.sep + f) for f in logs_list]

# Dictionary that stores tests information
test_dict      = {}

# Open each file start a dictionary:
# Testname
# |
# |_PC
# |  |
# |  |_Various Perf Couneters (From RTL)
# |
# |_IC (Inactivity Counter)
# |  |
# |  |_Various Probes Signals in Issue Stage
# |  
# |_INSTR_DICT (Used only if Tracer is available)
# 
for x_logs in logs_list_path:
    test_dict.setdefault(os.path.basename(x_logs).replace('.log',''),{})
    with open(x_logs, 'r') as x_log:
        pc_cnt = 0
        pc_en = 1
        mp_en = 0
        inactivity_en = 0
        an_test = os.path.basename(x_logs).replace('.log','')
        test_dict[an_test].setdefault('PC',{})
        test_dict[an_test].setdefault('IC',{})
        test_dict[an_test].setdefault('MP',{})
        test_dict[an_test].setdefault('instr_dict',{})
        for line in x_log:
            if (any(perf_counter in line for perf_counter in perf_counters) and pc_en):
                pc_value = [int(s) for s in line.split() if s.isdigit()]
                test_dict[an_test]['PC'].setdefault(perf_counters[pc_cnt],int(pc_value[0]))
                pc_cnt += 1
            if(any(inac_counter in line for inac_counter in inactivity_counters) and inactivity_en):
                pc_value = [int(s) for s in line.split() if s.isdigit()]
                test_dict[an_test]['IC'].setdefault(inactivity_counters[pc_cnt],int(pc_value[0]))
                pc_cnt += 1
            if(any(mp_counter in line for mp_counter in miss_prediction_counters) and mp_en):
                pc_value = [int(s) for s in line.split() if s.isdigit()]
                test_dict[an_test]['MP'].setdefault(miss_prediction_counters[pc_cnt],int(pc_value[0]))
                pc_cnt += 1

            if(pc_cnt == len(perf_counters) and (pc_en == 1)):
                pc_en = 0
                mp_en = 1
                pc_cnt = 0

            if(pc_cnt == len(miss_prediction_counters) and (mp_en == 1)):                
                mp_en = 0
                inactivity_en = 1
                pc_cnt = 0

        cycles = test_dict[an_test]['PC']['pc_cycles']
        instructions = test_dict[an_test]['PC']['pc_instr']
        test_dict[an_test]['PC'].setdefault('IPC', instructions/cycles)

# Sorting the tests by their name
sort_test_names = []
for k,v in test_dict.items():
    sort_test_names.append(k)
sort_test_names.sort()

# .CSV File if needed for some kind of Analysis. It lists the tests in alphabetical order
# and show the simple test info: Cycles, Instrcuntion retired, IPC.
fcsv = open('Test_analysis.csv','w')
fcsv.write('TEST,CYCLES,INSTRUCTIONS,IPC\n')
for test in sort_test_names:
    fcsv.write('%s,%d,%d,%f\n' % (test, test_dict[test]['PC']['pc_cycles'],test_dict[test]['PC']['pc_instr'],test_dict[test]['PC']['IPC']))
fcsv.close()

# Sort the Tests by their IPC
sort_ipc = sorted(test_dict, key=lambda x: test_dict[x]['PC']['IPC'])
for x in sort_ipc:
    sort_pc = sorted(test_dict[x]['PC'], key=lambda k: test_dict[x]['PC'][k], reverse=True)

# Trace Analyzer, Uncomment only if tracer is working. To test if it works in 32-bit mode
'''    
#Open the various traces
for traces in traces_list_path:
    with open(traces, 'r') as trace:
        # Initialize the variables:
        # instr_dict = collects each instructions and the number of cycles it takes each time it appears
        # ccyc = The cycle number of the current line
        # ocyc = The cycle number of the last line
        # big_line = Contains the string that are going to be written in the report.
        temp_instr = 0
        en_analysis = 0
        instr_dict= {}
        instr_list= []
        instr_counter = 0
        ccyc = 0
        ocyc = 0
        old_instr = ''
        big_line = []
        trace_name = os.path.basename(trace.name).replace('-trace.log','')
        for lcnt, line in enumerate(trace):
            # On each trace line we get the values of:
            # iaddr = instruction address
            # cyc = current cycle
            # imnem = instruction mnemonic
            splitted_line=line.split()
            iaddr = splitted_line[3]
            if('mcycle' in line):
                if (en_analysis):
                    break
                en_analysis ^= 1

            if(en_analysis):
                ccyc = splitted_line[1]
                imnem = splitted_line[6]
                dcyc = int(ccyc) - int(ocyc)
                if (dcyc == 0):
                    temp_instr = imnem
                else:
                    if(temp_instr != 0):
                        test_dict[trace_name]['instr_dict'].setdefault(imnem,[0,[]])
                        test_dict[trace_name]['instr_dict'][imnem][0] += 1
                        test_dict[trace_name]['instr_dict'][imnem][1].append(dcyc)
                        test_dict[trace_name]['instr_dict'].setdefault(temp_instr,[0,[]])
                        test_dict[trace_name]['instr_dict'][temp_instr][0] += 1
                        test_dict[trace_name]['instr_dict'][temp_instr][1].append(dcyc)
                    else:
                        test_dict[trace_name]['instr_dict'].setdefault(imnem,[0,[]])
                        test_dict[trace_name]['instr_dict'][imnem][0] += 1
                        test_dict[trace_name]['instr_dict'][imnem][1].append(dcyc)
                    temp_instr = 0
                if (dcyc > 20):
                    big_line.append(line+'\tLine number is %d\tDelta is %d  '% (lcnt,dcyc)+'*'*int(dcyc/5) +'\n\n' )
            ocyc = splitted_line[1]

        if not os.path.exists('./results/analysis/'):
            os.makedirs('./results/analysis/')
        ta = open('./results/analysis/'+trace_name+'-analysis.txt','w')
        for x in big_line:
            ta.write(x)
        ta.close()
        tot_instr = 0
        for x in list(test_dict[trace_name]['instr_dict']):
           tot_instr += test_dict[trace_name]['instr_dict'][x][0]
        if not os.path.exists('./results/recap/'):
            os.makedirs('./results/recap/')
        ta = open('./results/recap/'+trace_name+'-recap.csv','w')
        ta.write('INSTRUCTION,AVERAGE,STD,MIN,MAX,COUNT,PERC\n')
        for x in list(test_dict[trace_name]['instr_dict']):
            ta.write(x+','
                     +str(np.average(test_dict[trace_name]['instr_dict'][x][1]))+','
                     +str(np.std(test_dict[trace_name]['instr_dict'][x][1]))+','
                     +str(np.min(test_dict[trace_name]['instr_dict'][x][1]))+','
                     +str(np.max(test_dict[trace_name]['instr_dict'][x][1]))+','
                     +str(test_dict[trace_name]['instr_dict'][x][0])+','
                     +str(test_dict[trace_name]['instr_dict'][x][0]/tot_instr*100)+'\n')
        ta.close()
'''

# Automated Excel File Construction

# Create name for the Excel File
workbook = xlsxwriter.Workbook('Tests_analysis.xls')

# Some Format Styles that can be used in the Workbook
bold = workbook.add_format({'bold': True, 'align':'center'})
al_right = workbook.add_format({'align':'right'})
al_center = workbook.add_format({'align':'center'})
count_format = workbook.add_format()
count_format.set_num_format('#,##0')
count_format.set_align('center')
decimal_format = workbook.add_format()
decimal_format.set_num_format('0.000')
decimal_format.set_align('center')

# First Page of the Workbook, used to Create the Graph
graph_sheet = workbook.add_worksheet('GraphWS')
graph_sheet.write('A1','Test')
graph_sheet.write('B1','Instr')
graph_sheet.write('C1','Mult b2b')
graph_sheet.write('D1','RS FPU')
graph_sheet.write('E1','FF Empty')
graph_sheet.write('F1','RS Load')
graph_sheet.write('G1','RS Store')
graph_sheet.write('H1','RS ALU')
graph_sheet.write('I1','RS CTRL Flow')
graph_sheet.write('J1','RS CSR')
graph_sheet.write('K1','RS Mult')
graph_sheet.write('L1','Scoreboard Full')
graph_sheet.write('M1','WAW')
graph_sheet.write('N1','FU Load-Store')
graph_sheet.write('O1','FU FLU')
graph_sheet.write('P1','FU FPU')
graph_sheet.write('Q1','TOTAL')
graph_sheet.write('R1','CYCLES')

tt_counters = ['multb2b', 'rs_fpu', 'rs_load', 'rs_store', 'rs_alu', 'rs_ctrl_flow', 'rs_csr', 'rs_mult', 'scoreboard_full', 'waw', 'fu_load_store', 'fu_flu', 'fu_fpu']

# For each Test go throuth their Instruction Analysis (from Tracer), Performance Counters and Inactivity Counters
for index,x in enumerate(sort_ipc):
    # Create the Worksheet for the Test
    worksheet = workbook.add_worksheet(x)
#    for col in range(15):
    worksheet.set_column(0,2,13)
    worksheet.set_column(3,4,8)
    worksheet.set_column(5,16,13)
    # Sort the varouse classes by their apparition
    sort_instr  = sorted(test_dict[x]['instr_dict'],    key=lambda k: test_dict[x]['instr_dict'][k][0], reverse=True)
    sort_pc     = sorted(test_dict[x]['PC'],            key=lambda k: test_dict[x]['PC'][k],            reverse=True)
    sort_ic     = sorted(test_dict[x]['IC'],            key=lambda k: test_dict[x]['IC'][k],            reverse=True)
    # Remove some Information, will be written Directly on Top of the page
    sort_pc.remove('pc_cycles')
    sort_pc.remove('pc_instr')
    sort_pc.remove('IPC')
    worksheet.write('A1','INSTRUCTION'  ,bold)
    worksheet.write('B1','AVG'          ,bold)
    worksheet.write('C1','STD'          ,bold)
    worksheet.write('D1','MIN'          ,bold)
    worksheet.write('E1','MAX'          ,bold)
    worksheet.write('F1','COUNT'        ,bold)
    worksheet.write('G1','PERC'         ,bold)
    worksheet.write('I1','PC'           ,bold)
    worksheet.write('J1','VALUE'        ,bold)
    worksheet.write('I20','IC'          ,bold)
    worksheet.write('J20','VALUE'       ,bold)
    worksheet.write('K20','Main Stalls'         ,bold)
    worksheet.write('M20','Issue Inactivity'    ,bold)
    worksheet.write('O20','Resiger Unavailable' ,bold)
    worksheet.write('Q20','Busy FU'     ,bold)
    worksheet.write('K1','CYCLES'       ,bold)
    worksheet.write('L1','INSTR'        ,bold)
    worksheet.write('M1','IPC'          ,bold)
    worksheet.write('K2',test_dict[x]['PC']['pc_cycles']   ,count_format   )
    worksheet.write('L2',test_dict[x]['PC']['pc_instr']    ,count_format   )
    worksheet.write('M2',test_dict[x]['PC']['IPC']         ,decimal_format )
    tot_instr = 0

    # Writing of the Instructions Analysis
    for y in list(test_dict[x]['instr_dict']):
        tot_instr += test_dict[x]['instr_dict'][y][0]
    for npc,y in enumerate(sort_instr):
        worksheet.write(npc+1, 0, y, al_right)
        worksheet.write(npc+1, 1, np.average(test_dict[x]['instr_dict'][y][1]), decimal_format)
        worksheet.write(npc+1, 2, np.std(test_dict[x]['instr_dict'][y][1]), decimal_format)
        worksheet.write(npc+1, 3, np.min(test_dict[x]['instr_dict'][y][1]), al_center)
        worksheet.write(npc+1, 4, np.max(test_dict[x]['instr_dict'][y][1]), al_center)
        worksheet.write(npc+1, 5, test_dict[x]['instr_dict'][y][0], count_format)
        worksheet.write(npc+1, 6, test_dict[x]['instr_dict'][y][0]/tot_instr*100, decimal_format)
    for npc,y in enumerate(sort_pc):
        worksheet.write(npc+1, 8, y)
        worksheet.write(npc+1, 9, test_dict[x]['PC'][y], count_format)
    for npc,y in enumerate(sort_ic):
        worksheet.write(npc+20,8, y)
        worksheet.write(npc+20,9, test_dict[x]['IC'][y], count_format)

    #Main Stalls
    worksheet.write('K21','instr')
    worksheet.write('K22','fetch_fifo_empty')
    worksheet.write('K23','issue_inactivity')
    worksheet.write('L21',test_dict[x]['PC']['pc_instr'])
    worksheet.write('L22',test_dict[x]['PC']['pc_fetch_fifo_empty'])
    worksheet.write('L23',test_dict[x]['IC']['total_inactivity'])
    #Issue Inactivity
    worksheet.write('M21','register_unavailable')
    worksheet.write('M22','scoreboard_full')
    worksheet.write('M23','waw')
    worksheet.write('M24','multb2b')
    worksheet.write('M25','fu_busy')
    worksheet.write('N21',test_dict[x]['IC']['register_unavailable'])
    worksheet.write('N22',test_dict[x]['IC']['scoreboard_full'])
    worksheet.write('N23',test_dict[x]['IC']['waw'])
    worksheet.write('N24',test_dict[x]['IC']['multb2b'])
    worksheet.write('N25',test_dict[x]['IC']['fu_busy'])
    #Register Unavailable
    worksheet.write('O21','rs_store')
    worksheet.write('O22','rs_load')
    worksheet.write('O23','rs_alu')
    worksheet.write('O24','rs_ctrl_flow')
    worksheet.write('O25','rs_csr')
    worksheet.write('O26','rs_mult')
    worksheet.write('O27','rs_fpu')
    worksheet.write('P21',test_dict[x]['IC']['rs_store'])
    worksheet.write('P22',test_dict[x]['IC']['rs_load'])
    worksheet.write('P23',test_dict[x]['IC']['rs_alu'])
    worksheet.write('P24',test_dict[x]['IC']['rs_ctrl_flow'])
    worksheet.write('P25',test_dict[x]['IC']['rs_csr'])
    worksheet.write('P26',test_dict[x]['IC']['rs_mult'])
    worksheet.write('P27',test_dict[x]['IC']['rs_fpu'])
    #Functional Units Busy
    worksheet.write('Q21','fu_load_store')
    worksheet.write('Q22','fu_flu')
    worksheet.write('Q23','fu_fpu')
    worksheet.write('R21',test_dict[x]['IC']['fu_load_store'])
    worksheet.write('R22',test_dict[x]['IC']['fu_flu'])
    worksheet.write('R23',test_dict[x]['IC']['fu_fpu'])
    #Misprediction Info
    worksheet.write('P1','Tot Branches' ,bold)
    worksheet.write('P2','MP Rate'      ,bold)
    worksheet.write('P3','BHT'    ,bold)
    worksheet.write('P4','BTB'    ,bold)
    worksheet.write('P5','RAS'    ,bold)

    worksheet.write('Q1',test_dict[x]['MP']['Total Resolved branches'])
    tot_mispred = test_dict[x]['MP']['BHT'] + test_dict[x]['MP']['BTB'] + test_dict[x]['MP']['RAS']
    worksheet.write('Q2',tot_mispred/test_dict[x]['MP']['Total Resolved branches']*100 ,decimal_format )
    worksheet.write('Q3',test_dict[x]['MP']['BHT'])
    worksheet.write('Q4',test_dict[x]['MP']['BTB'])
    worksheet.write('Q5',test_dict[x]['MP']['RAS'])
    
    tot_cycles = 0
    for to_sum in tt_counters:
        tot_cycles += int(test_dict[x]['IC'][to_sum])
    tot_cycles += test_dict[x]['PC']['pc_instr']
    tot_cycles += test_dict[x]['PC']['pc_fetch_fifo_empty']

    #GraphData
    graph_sheet.write(index+1, 0 , x                                                           )
    graph_sheet.write(index+1, 1 , test_dict[x]['PC']['pc_instr'            ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 2 , test_dict[x]['IC']['multb2b'             ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 3 , test_dict[x]['IC']['rs_fpu'              ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 4 , test_dict[x]['PC']['pc_fetch_fifo_empty' ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 5 , test_dict[x]['IC']['rs_load'             ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 6 , test_dict[x]['IC']['rs_store'            ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 7 , test_dict[x]['IC']['rs_alu'              ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 8 , test_dict[x]['IC']['rs_ctrl_flow'        ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 9 , test_dict[x]['IC']['rs_csr'              ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 10, test_dict[x]['IC']['rs_mult'             ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 11, test_dict[x]['IC']['scoreboard_full'     ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 12, test_dict[x]['IC']['waw'                 ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 13, test_dict[x]['IC']['fu_load_store'       ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 14, test_dict[x]['IC']['fu_flu'              ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 15, test_dict[x]['IC']['fu_fpu'              ]/tot_cycles * 100 )
    graph_sheet.write(index+1, 16, tot_cycles                                                  )
    graph_sheet.write(index+1, 17, test_dict[x]['PC']['pc_cycles']                             )


workbook.close()
