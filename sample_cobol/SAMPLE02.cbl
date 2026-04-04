000010 IDENTIFICATION DIVISION.                                         
000020 PROGRAM-ID. SAMPLE02.                                             
000030*    算術文とCALL文のテスト用サンプル                               
000040 DATA DIVISION.                                                    
000050 WORKING-STORAGE SECTION.                                          
000060 01 WK-CALC-AREA.                                                  
000070   05 WK-PRICE       PIC 9(07) VALUE 1000.                         
000080   05 WK-QTY         PIC 9(03) VALUE 5.                            
000090   05 WK-SUBTOTAL    PIC 9(09).                                    
000100   05 WK-TAX-RATE    PIC V99   VALUE 0.10.                         
000110   05 WK-TAX-AMT     PIC 9(07).                                    
000120   05 WK-GRAND-TOTAL PIC 9(09).                                    
000130   05 WK-DISCOUNT    PIC 9(05).                                    
000140   05 WK-RESULT      PIC 9(09).                                    
000150 01 WK-CALL-AREA.                                                  
000160   05 WK-PARAM1      PIC X(10).                                    
000170   05 WK-PARAM2      PIC X(10).                                    
000180   05 WK-RETURN-CD   PIC 9(02).                                    
000190 PROCEDURE DIVISION.                                               
000200 CALC-PROC.                                                        
000210*    MULTIPLY GIVING: 正常（VALUE句ありの変数を参照のみ）          
000220     MULTIPLY WK-PRICE BY WK-QTY                                   
000230         GIVING WK-SUBTOTAL.                                       
000240*    COMPUTE: 正常（WK-SUBTOTALは代入済み）                        
000250     COMPUTE WK-TAX-AMT = WK-SUBTOTAL * WK-TAX-RATE.              
000260*    ADD: Override警告（WK-PRICEはVALUE句あり）                    
000270     ADD WK-TAX-AMT TO WK-PRICE.                                   
000280*    未初期化参照（WK-DISCOUNTは未初期化）                         
000290     SUBTRACT WK-DISCOUNT FROM WK-SUBTOTAL                         
000300         GIVING WK-GRAND-TOTAL.                                    
000310*    DIVIDE: WK-RESULTへの代入                                     
000320     DIVIDE WK-GRAND-TOTAL BY 2                                    
000330         GIVING WK-RESULT.                                         
000340*    CALL文: WK-PARAM1, WK-PARAM2は未初期化で参照渡し             
000350     CALL 'SUBPGM01' USING WK-PARAM1 WK-PARAM2.                   
000360*    未初期化参照（WK-RETURN-CDは未初期化）                        
000370     IF WK-RETURN-CD = 0                                           
000380         DISPLAY 'OK'                                              
000390     ELSE                                                          
000400         DISPLAY 'NG'                                              
000410     END-IF.                                                       
000420     STOP RUN.                                                     
