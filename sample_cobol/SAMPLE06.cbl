000010 IDENTIFICATION DIVISION.                                         
000020 PROGRAM-ID. SAMPLE06.                                            
000030*    VALUE句の初期値を参照した後に上書きされる危険パターン         
000040 DATA DIVISION.                                                   
000050 WORKING-STORAGE SECTION.                                         
000060*--- 税率マスタ（定数として使う想定）---                           
000070 01 WK-TAX-MASTER.                                                
000080   05 WK-TAX-RATE   PIC V99  VALUE 0.10.                          
000090   05 WK-TAX-NAME   PIC X(10) VALUE 消費税.                    
000100*--- 割引率（定数として使う想定）---                               
000110 01 WK-DISCOUNT-AREA.                                             
000120   05 WK-DISC-RATE  PIC V99  VALUE 0.20.                          
000130   05 WK-DISC-NAME  PIC X(10) VALUE 会員割引.                  
000140*--- 計算ワーク ---                                                
000150 01 WK-CALC.                                                      
000160   05 WK-PRICE      PIC 9(07).                                    
000170   05 WK-TAX-AMT    PIC 9(07).                                    
000180   05 WK-DISC-AMT   PIC 9(07).                                    
000190   05 WK-TOTAL      PIC 9(08).                                    
000200   05 WK-MSG        PIC X(40).                                    
000210 PROCEDURE DIVISION.                                              
000220 MAIN-PROC.                                                       
000230     MOVE 10000 TO WK-PRICE.                                      
000240*--- 正常: VALUE句の初期値を参照して税額計算 ---                   
000250     COMPUTE WK-TAX-AMT = WK-PRICE * WK-TAX-RATE.                
000260     DISPLAY WK-TAX-NAME.                                         
000270     DISPLAY WK-TAX-AMT.                                          
000280*--- 危険: 定数のはずの税率を上書き（バグの可能性大）---           
000290     MOVE 0.08 TO WK-TAX-RATE.                                    
000300*--- この後の計算は意図しない税率で行われる ---                     
000310     COMPUTE WK-TAX-AMT = WK-PRICE * WK-TAX-RATE.                
000320*--- 正常: VALUE句の初期値を参照して割引計算 ---                   
000330     COMPUTE WK-DISC-AMT = WK-PRICE * WK-DISC-RATE.              
000340     DISPLAY WK-DISC-NAME.                                        
000350*--- 危険: 定数のはずの割引率を上書き ---                          
000360     MOVE 0.30 TO WK-DISC-RATE.                                   
000370*--- 危険: 定数のはずの割引名を上書き ---                          
000380     MOVE 特別割引 TO WK-DISC-NAME.                            
000390*--- 危険: 定数のはずの税率名を上書き ---                          
000400     MOVE 軽減税率 TO WK-TAX-NAME.                             
000410*--- 合計計算（上書き後の値で計算される）---                        
000420     COMPUTE WK-TOTAL = WK-PRICE + WK-TAX-AMT - WK-DISC-AMT.     
000430     DISPLAY WK-TOTAL.                                            
000440     STOP RUN.                                                    

