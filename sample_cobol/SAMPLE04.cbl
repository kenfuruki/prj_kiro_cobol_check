000010 IDENTIFICATION DIVISION.                                         
000020 PROGRAM-ID. SAMPLE04.                                             
000030*    グループ項目の初期化波及とPERFORM VARYINGのテスト             
000040 DATA DIVISION.                                                    
000050 WORKING-STORAGE SECTION.                                          
000060 01 WK-RECORD VALUE SPACES.                                        
000070   05 WK-ID          PIC X(05).                                    
000080   05 WK-NAME        PIC X(20).                                    
000090   05 WK-DEPT        PIC X(10).                                    
000100 01 WK-TABLE-AREA.                                                 
000110   05 WK-TABLE OCCURS 10 TIMES.                                    
000120     10 WK-TBL-KEY   PIC X(05).                                    
000130     10 WK-TBL-VAL   PIC 9(05).                                    
000140 01 WK-COUNTERS.                                                   
000150   05 WK-IDX         PIC 9(03).                                    
000160   05 WK-MAX         PIC 9(03) VALUE 10.                           
000170   05 WK-SUM         PIC 9(09).                                    
000180   05 WK-AVG         PIC 9(07).                                    
000190 01 WK-FLAGS.                                                      
000200   05 WK-EOF-FLG     PIC X(01) VALUE 'N'.                          
000210     88 WK-EOF       VALUE 'Y'.                                    
000220   05 WK-ERR-FLG     PIC X(01).                                    
000230 PROCEDURE DIVISION.                                               
000240 MAIN-PROC.                                                        
000250*    グループ項目VALUE SPACESで子は初期化済み → 警告なし           
000260     DISPLAY WK-ID.                                                
000270     DISPLAY WK-NAME.                                              
000280     DISPLAY WK-DEPT.                                              
000290*    PERFORM VARYING: WK-IDXは制御変数として代入扱い              
000300     INITIALIZE WK-SUM.                                            
000310     PERFORM VARYING WK-IDX FROM 1 BY 1                            
000320         UNTIL WK-IDX > WK-MAX                                     
000330         ADD WK-TBL-VAL(WK-IDX) TO WK-SUM                         
000340     END-PERFORM.                                                  
000350*    WK-SUMは代入済み、WK-MAXはVALUE句あり → 正常                 
000360     DIVIDE WK-SUM BY WK-MAX GIVING WK-AVG.                        
000370     DISPLAY WK-AVG.                                               
000380*    Override警告（WK-EOF-FLGはVALUE句あり）                       
000390     MOVE 'Y' TO WK-EOF-FLG.                                       
000400*    未初期化参照（WK-ERR-FLGは未初期化）                          
000410     IF WK-ERR-FLG = 'E'                                           
000420         DISPLAY 'ERROR OCCURRED'                                  
000430     END-IF.                                                       
000440     STOP RUN.                                                     
