000010 IDENTIFICATION DIVISION.                                         
000020 PROGRAM-ID. SAMPLE03.                                             
000030*    STRING/UNSTRING/READ INTO/ACCEPTのテスト用サンプル            
000040 ENVIRONMENT DIVISION.                                             
000050 INPUT-OUTPUT SECTION.                                             
000060 FILE-CONTROL.                                                     
000070     SELECT INPUT-FILE ASSIGN TO 'INPUT.DAT'.                      
000080 DATA DIVISION.                                                    
000090 FILE SECTION.                                                     
000100 FD INPUT-FILE.                                                    
000110 01 INPUT-REC         PIC X(80).                                   
000120 WORKING-STORAGE SECTION.                                          
000130 01 WK-STRING-AREA.                                                
000140   05 WK-LAST-NAME   PIC X(10).                                    
000150   05 WK-FIRST-NAME  PIC X(10).                                    
000160   05 WK-FULL-NAME   PIC X(21).                                    
000170   05 WK-SEPARATOR   PIC X(01) VALUE ' '.                          
000180 01 WK-UNSTRING-AREA.                                              
000190   05 WK-INPUT-LINE  PIC X(50) VALUE 'TOKYO,OSAKA,NAGOYA'.         
000200   05 WK-CITY1       PIC X(10).                                    
000210   05 WK-CITY2       PIC X(10).                                    
000220   05 WK-CITY3       PIC X(10).                                    
000230 01 WK-READ-AREA.                                                  
000240   05 WK-FILE-DATA   PIC X(80).                                    
000250 01 WK-ACCEPT-AREA.                                                
000260   05 WK-USER-INPUT  PIC X(30).                                    
000270   05 WK-DATE-TODAY  PIC 9(08).                                    
000280 01 WK-MISC.                                                       
000290   05 WK-UNUSED-VAR  PIC X(10).                                    
000300   05 WK-ORPHAN      PIC 9(05).                                    
000310 PROCEDURE DIVISION.                                               
000320 STRING-PROC.                                                      
000330*    未初期化参照（WK-LAST-NAME, WK-FIRST-NAMEは未初期化）        
000340     STRING WK-LAST-NAME DELIMITED BY SPACE                        
000350            WK-SEPARATOR DELIMITED BY SIZE                         
000360            WK-FIRST-NAME DELIMITED BY SPACE                       
000370         INTO WK-FULL-NAME.                                        
000380*    Override警告（WK-SEPARATORはVALUE句あり）                     
000390     MOVE '-' TO WK-SEPARATOR.                                     
000400 UNSTRING-PROC.                                                    
000410*    Override警告（WK-INPUT-LINEはVALUE句あり + 参照）            
000420     UNSTRING WK-INPUT-LINE DELIMITED BY ','                       
000430         INTO WK-CITY1 WK-CITY2 WK-CITY3.                         
000440     DISPLAY WK-CITY1.                                             
000450     DISPLAY WK-CITY2.                                             
000460     DISPLAY WK-CITY3.                                             
