000010 IDENTIFICATION DIVISION.                                         
000020 PROGRAM-ID. SAMPLE05.                                             
000030*    警告なしの正常パターン集                                      
000040 DATA DIVISION.                                                    
000050 WORKING-STORAGE SECTION.                                          
000060 01 WK-CLEAN-AREA.                                                 
000070   05 WK-A           PIC X(10).                                    
000080   05 WK-B           PIC X(10).                                    
000090   05 WK-C           PIC 9(05).                                    
000100   05 WK-D           PIC 9(05).                                    
000110   05 WK-E           PIC X(20).                                    
000120 PROCEDURE DIVISION.                                               
000130 CLEAN-PROC.                                                       
000140*    代入してから参照 → 正常                                       
000150     MOVE 'HELLO' TO WK-A.                                         
000160     DISPLAY WK-A.                                                 
000170*    INITIALIZE後に参照 → 正常                                     
000180     INITIALIZE WK-B.                                              
000190     DISPLAY WK-B.                                                 
000200*    ACCEPT後に参照 → 正常                                         
000210     ACCEPT WK-C FROM DATE.                                        
000220     DISPLAY WK-C.                                                 
000230*    COMPUTE代入後に参照 → 正常                                    
000240     COMPUTE WK-D = WK-C + 100.                                    
000250     DISPLAY WK-D.                                                 
000260*    MOVE後にMOVE → 正常（上書きだがVALUE句なし）                  
000270     MOVE 'FIRST' TO WK-E.                                         
000280     MOVE 'SECOND' TO WK-E.                                        
000290     DISPLAY WK-E.                                                 
000300     STOP RUN.                                                     
