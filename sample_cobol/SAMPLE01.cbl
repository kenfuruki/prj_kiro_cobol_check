000010 IDENTIFICATION DIVISION.                                         
000020 PROGRAM-ID. SAMPLE01.                                             
000030 DATA DIVISION.                                                    
000040 WORKING-STORAGE SECTION.                                          
000050 01 WK-AREA.                                                       
000060   05 WK-NAME        PIC X(20) VALUE 'TANAKA'.                     
000070   05 WK-AGE         PIC 9(03) VALUE 25.                           
000080   05 WK-SALARY      PIC 9(07).                                    
000090   05 WK-TAX         PIC 9(07).                                    
000100   05 WK-NET-SALARY  PIC 9(07).                                    
000110   05 WK-BONUS       PIC 9(07) VALUE 100000.                       
000120   05 WK-TOTAL       PIC 9(08).                                    
000130   05 WK-MSG         PIC X(30).                                    
000140   05 WK-COUNTER     PIC 9(03).                                    
000150   05 WK-TEMP        PIC X(10).                                    
000160 PROCEDURE DIVISION.                                               
000170 MAIN-PROC.                                                        
000180*    VALUE句で初期化済みの変数を上書き（Override警告が出るはず）     
000190     MOVE 'SUZUKI' TO WK-NAME.                                     
000200     MOVE 30 TO WK-AGE.                                            
000210*    未初期化変数を参照（Uninitialized警告が出るはず）              
000220     DISPLAY WK-SALARY.                                            
000230     DISPLAY WK-TAX.                                               
000240*    未初期化変数を使って計算（Uninitialized警告が出るはず）        
000250     COMPUTE WK-NET-SALARY = WK-SALARY - WK-TAX.                   
000260*    VALUE句で初期化済みの変数を上書き（Override警告が出るはず）     
000270     MOVE 200000 TO WK-BONUS.                                      
000280*    正常: 代入してから参照                                         
000290     MOVE 500000 TO WK-SALARY.                                     
000300     COMPUTE WK-TOTAL = WK-SALARY + WK-BONUS.                      
000310     DISPLAY WK-TOTAL.                                             
000320*    未初期化変数を参照（Uninitialized警告が出るはず）              
000330     DISPLAY WK-MSG.                                               
000340*    INITIALIZE後の参照は問題なし                                   
000350     INITIALIZE WK-COUNTER.                                        
000360     DISPLAY WK-COUNTER.                                           
000370*    未初期化変数を参照（Uninitialized警告が出るはず）              
000380     MOVE WK-TEMP TO WK-MSG.                                       
000390     STOP RUN.                                                     
