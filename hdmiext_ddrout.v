module hdmiext_ddrout(input [2:0] tmds,
		      input  tmds_clock,
		      output r_pad_p,
		      output r_pad_n,
		      output g_pad_p,
		      output g_pad_n,
		      output b_pad_p,
		      output b_pad_n,
		      output clk_pad_p,
		      output clk_pad_n);
OBUFDS #(.IOSTANDARD("TMDS_33"))   obufds_red(.I(tmds[2]),    .O(r_pad_p),   .OB(r_pad_n));
OBUFDS #(.IOSTANDARD("TMDS_33")) obufds_green(.I(tmds[1]),    .O(g_pad_p),   .OB(g_pad_n));
OBUFDS #(.IOSTANDARD("TMDS_33"))  obufds_blue(.I(tmds[0]),    .O(b_pad_p),   .OB(b_pad_n));
OBUFDS #(.IOSTANDARD("TMDS_33")) obufds_clock(.I(tmds_clock), .O(clk_pad_p), .OB(clk_pad_n));
endmodule
